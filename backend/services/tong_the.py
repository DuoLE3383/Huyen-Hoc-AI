"""Tổng hợp toàn bộ: phong thủy + sự kiện + môi trường + vĩ mô."""
import json
import os
from datetime import date, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from database import SavedEvent, User, get_db
from phong_thuy import phan_tich_toan_dien
from su_kien import quet_su_kien_tuan
from moi_truong import (
    WeatherProviderError,
    danh_gia_anh_huong_moi_truong,
    lay_du_lieu_moi_truong,
)
from vi_mo import timeline_vi_mo
from ket_noi import buc_tranh_tong_the
from astrology import phan_tich_ngay_sinh
from services.narrative import (
    generate_tong_the_narrative,
    stream_tong_the_narrative,
)

router = APIRouter(prefix="/api/tong-the", tags=["tong-the"])


class CombinedInput(BaseModel):
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)
    gioi_tinh: Literal["nam", "nu"] = "nam"
    huong_nha: str = "Nam"
    huong_bep: str | None = None
    huong_phong_ngu: str | None = None
    muc_dich: Literal[
        "tai_van", "suc_khoe", "tinh_cam", "su_nghiep", "hoc_tap", "tam_linh"
    ] = "tai_van"
    ngay_bat_dau: date | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _validate_coords(self) -> "CombinedInput":
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Cần nhập đồng thời vĩ độ và kinh độ.")
        return self


def _sse(name: str, payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    return f"event: {name}\ndata: {body}\n\n"


async def _build_tong_the(data: CombinedInput, user: User, db: Session) -> dict[str, Any]:
    try:
        phong_thuy = phan_tich_toan_dien(
            data.ngay, data.thang, data.nam, data.gioi_tinh,
            data.huong_nha, data.huong_bep, data.huong_phong_ngu,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    start = data.ngay_bat_dau or date.today()
    end = start + timedelta(days=6)
    events = (
        db.query(SavedEvent)
        .filter(
            SavedEvent.user_id == user.id,
            SavedEvent.ngay >= start.isoformat(),
            SavedEvent.ngay <= end.isoformat(),
        )
        .order_by(SavedEvent.ngay.asc())
        .all()
    )
    event_summary = quet_su_kien_tuan(
        [{"id": e.id, "loai": e.loai, "ngay": e.ngay, "note": e.ghi_chu} for e in events],
        start,
    )

    profile = phan_tich_ngay_sinh(data.ngay, data.thang, data.nam)

    environment = None
    if data.lat is not None and data.lon is not None:
        if not os.getenv("OPENWEATHER_API_KEY", "").strip():
            raise HTTPException(503, "Dịch vụ môi trường chưa được cấu hình.")
        try:
            environment = await lay_du_lieu_moi_truong(data.lat, data.lon)
        except WeatherProviderError as exc:
            raise HTTPException(502, str(exc))
        environment["danh_gia"] = danh_gia_anh_huong_moi_truong(environment)

    vi_mo = timeline_vi_mo(start, 90)
    tong_hop = buc_tranh_tong_the(profile, phong_thuy, event_summary, environment)

    return {
        "phong_thuy": phong_thuy,
        "su_kien": event_summary,
        "moi_truong": environment,
        "vi_mo": vi_mo,
        "profile": profile,
        "tong_hop": tong_hop,
    }


@router.post("/")
async def api_tong_the(
    data: CombinedInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = await _build_tong_the(data, user, db)
    narrative = await generate_tong_the_narrative(result)
    return {**result, "ai_narrative": narrative}


@router.post("/stream")
async def api_tong_the_stream(
    data: CombinedInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await _build_tong_the(data, user, db)

    async def event_stream():
        yield _sse("metadata", {
            "phong_thuy": result["phong_thuy"],
            "su_kien": result["su_kien"],
            "moi_truong": result["moi_truong"],
            "vi_mo": result["vi_mo"],
            "profile": result["profile"],
        })

        async for chunk in stream_tong_the_narrative(result):
            if chunk["type"] == "token":
                yield _sse("token", {"content": chunk["content"]})
            elif chunk["type"] == "error":
                yield _sse("error", {"message": chunk["message"]})
                return
            elif chunk["type"] == "done":
                yield _sse("done", {"parsed": chunk["parsed"]})
                return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )