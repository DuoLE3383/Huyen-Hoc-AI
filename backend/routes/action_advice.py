"""Action advice API with optional streaming and per-user history."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import ActionAdviceLog, SessionLocal, User, get_db
from services.action_engine import (
    ACTIONS,
    build_action_advice,
    fetch_aqi_openweather,
    fetch_weather_openweather,
)
from services.narrative import stream_action_narrative

router = APIRouter(prefix="/api/action-advice", tags=["action-advice"])
LOCAL_TIMEZONE = timezone(timedelta(hours=7), name="ICT")


class ActionAdviceInput(BaseModel):
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)
    gio_sinh: int | None = Field(default=None, ge=0, le=23)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    thanh_pho: str | None = Field(default=None, max_length=120)
    quoc_gia: str | None = Field(default=None, max_length=80)
    gioi_tinh: Literal["nam", "nu"] = "nam"
    huong_nha: str = "Nam"
    muc_dich: Literal[
        "tai_van", "suc_khoe", "tinh_cam", "su_nghiep", "hoc_tap", "tam_linh"
    ] = "tai_van"
    hanh_dong: Literal[
        "xuat_hanh", "ky_ket", "gap_doi_tac", "khai_truong", "mua_sam_lon",
        "phong_van", "hoc_tap", "the_thao", "nghi_ngoi",
    ]
    xem_ngay: date | None = None


async def _build_advice(data: ActionAdviceInput, target_date: date) -> dict:
    weather = None
    aqi = None
    if data.lat is not None and data.lon is not None:
        weather = await fetch_weather_openweather(data.lat, data.lon)
        aqi = await fetch_aqi_openweather(data.lat, data.lon)
    try:
        return build_action_advice(
            action_key=data.hanh_dong,
            ngay_sinh=data.ngay,
            thang_sinh=data.thang,
            nam_sinh=data.nam,
            gioi_tinh=data.gioi_tinh,
            target_date=target_date,
            muc_dich=data.muc_dich,
            huong_nha=data.huong_nha,
            thanh_pho=data.thanh_pho,
            quoc_gia=data.quoc_gia,
            lat=data.lat,
            lon=data.lon,
            thoi_tiet=weather,
            aqi=aqi,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _save_log(
    db: Session, user_id: int, data: ActionAdviceInput, target_date: date, payload: dict
) -> ActionAdviceLog:
    log = ActionAdviceLog(
        user_id=user_id,
        hanh_dong=data.hanh_dong,
        xem_ngay=target_date.isoformat(),
        thanh_pho=data.thanh_pho,
        lat=data.lat,
        lon=data.lon,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _sse_event(name: str, payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {body}\n\n"


@router.get("/actions")
def list_actions(user: User = Depends(get_current_user)):
    del user
    return {
        "actions": [
            {"key": key, "ten": value["ten"], "mo_ta": value["mo_ta"]}
            for key, value in ACTIONS.items()
        ]
    }


@router.post("/")
async def action_advice(
    data: ActionAdviceInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_date = data.xem_ngay or datetime.now(LOCAL_TIMEZONE).date()
    advice = await _build_advice(data, target_date)
    log = _save_log(db, user.id, data, target_date, advice)
    return {
        "id": log.id,
        "ngay_xem": target_date.isoformat(),
        "lich_van_nien": advice["thoi_gian"],
        **advice,
    }


@router.post("/stream")
async def action_advice_stream(
    data: ActionAdviceInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_date = data.xem_ngay or datetime.now(LOCAL_TIMEZONE).date()
    advice = await _build_advice(data, target_date)

    # Persist before streaming and retain only primitive identifiers in the generator.
    user_id = user.id
    log = _save_log(db, user_id, data, target_date, advice)
    log_id = log.id
    metadata = {"id": log_id, **advice}

    async def event_stream():
        yield _sse_event("metadata", metadata)
        async for chunk in stream_action_narrative(advice):
            if chunk["type"] == "token":
                yield _sse_event("token", {"content": chunk["content"]})
            elif chunk["type"] == "done":
                history_db = SessionLocal()
                try:
                    saved_log = history_db.query(ActionAdviceLog).filter_by(
                        id=log_id, user_id=user_id
                    ).first()
                    if saved_log is not None:
                        saved_payload = json.loads(saved_log.payload_json)
                        saved_payload["ai_narrative"] = chunk["parsed"]
                        saved_log.payload_json = json.dumps(saved_payload, ensure_ascii=False)
                        history_db.commit()
                finally:
                    history_db.close()
                yield _sse_event("done", {"id": log_id, "parsed": chunk["parsed"]})
            elif chunk["type"] == "error":
                yield _sse_event("error", {"message": chunk["message"]})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
def advice_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
):
    rows = (
        db.query(ActionAdviceLog)
        .filter_by(user_id=user.id)
        .order_by(ActionAdviceLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "hanh_dong": row.hanh_dong,
                "xem_ngay": row.xem_ngay,
                "thanh_pho": row.thanh_pho,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.get("/history/{log_id}")
def advice_detail(
    log_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(ActionAdviceLog).filter_by(id=log_id, user_id=user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy gợi ý.")
    return {
        "id": row.id,
        "hanh_dong": row.hanh_dong,
        "xem_ngay": row.xem_ngay,
        "thanh_pho": row.thanh_pho,
        "payload": json.loads(row.payload_json),
        "created_at": row.created_at.isoformat(),
    }
