import hashlib
import json
import logging
import math
import os
import secrets
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Path as ApiPath, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import text

from ab_testing import assign_variant, experiment_metrics, record_experiment, record_feedback_reward, update_weights
from analytics import (
    accuracy_by_field,
    accuracy_timeline,
    apply_experimental_weights,
    bias_analysis,
    get_weights_from_history,
    top_patterns,
)
from astrology import phan_tich_ngay_sinh, tinh_chi_so_su_kien
from auth import (
    UserOut,
    UserRegister,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from database import (
    EventFeedback,
    Prediction,
    Profile,
    SavedEvent,
    TelegramLinkChallenge,
    User,
    get_db,
    init_db,
    utcnow_naive,
)
from lich_van_nien import (
    du_doan_thang,
    du_doan_tuan,
    phan_tich_ngay,
    tong_hop_thang,
    tong_hop_tuan,
)
from ollama_client import build_analysis_prompt, ollama
from pdf_export import export_ban_menh_pdf, export_la_so_pdf
from social import compatibility, create_share_link, get_share_link, revoke_share_link
from tarot import luan_giai_tarot
from kinh_dich import luan_giai_que
from tu_vi import lap_la_so
from phong_thuy import (
    HUONG,
    HUONG_THEO_MUC_DICH,
    phan_tich_toan_dien,
    phi_tinh_ngay,
)
from su_kien import EVENTS, danh_muc_su_kien, du_bao_dai_han, quet_su_kien_tuan
from moi_truong import WeatherProviderError, danh_gia_anh_huong_moi_truong, lay_du_lieu_moi_truong
from vi_mo import timeline_vi_mo
from ket_noi import buc_tranh_tong_the


@asynccontextmanager
async def lifespan(_app: FastAPI):
    del _app
    polling_task = None
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from notifications import polling_loop
        from scheduler import start_scheduler, stop_scheduler

        start_scheduler()
        polling_task = asyncio.create_task(polling_loop(), name="telegram-polling")
    try:
        yield
    finally:
        if polling_task is not None:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            stop_scheduler()


IS_PRODUCTION = os.getenv("APP_ENV", "").lower() == "production"
app = FastAPI(
    title="Huyền Học AI Pro",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

init_db()
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
EVENT_TYPES = {"tai_van", "tinh_duyen", "su_nghiep", "suc_khoe", "gap_go", "thay_doi"}
SCOPE_TYPES = {"general", "daily", "weekly", "monthly"}


def _get_owned_profile(
    db: Session, user: User, ngay_sinh: str | None = None
) -> Profile:
    query = db.query(Profile).filter(Profile.user_id == user.id)
    if ngay_sinh:
        query = query.filter(Profile.ngay_sinh == ngay_sinh)
    profile = query.order_by(Profile.id.asc()).first()
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Chưa có hồ sơ phù hợp. Hãy phân tích ngày sinh trước.",
        )
    return profile


def _parse_llm_json(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Ollama không trả về JSON hợp lệ.") from exc
    if not isinstance(data, dict):
        raise ValueError("Ollama phải trả về một object JSON.")
    return data


def _normalize_weekly_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    return [
        item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        for item in items
        if item is not None
    ]


def _ollama_http_error(exc: Exception) -> HTTPException:
    del exc
    return HTTPException(
        status_code=502,
        detail="Ollama không trả về kết quả sử dụng được; hãy kiểm tra dịch vụ và model.",
    )


class BirthInput(BaseModel):
    ho_ten: str = Field(default="", max_length=100)
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)

    @model_validator(mode="after")
    def validate_calendar_date(self) -> "BirthInput":
        try:
            date(self.nam, self.thang, self.ngay)
        except ValueError as exc:
            raise ValueError("Ngày sinh không hợp lệ.") from exc
        return self


class FeedbackInput(BaseModel):
    ngay_sinh: str = Field(min_length=10, max_length=10)
    loai_su_kien: Literal[
        "tai_van", "tinh_duyen", "su_nghiep", "suc_khoe", "gap_go", "thay_doi"
    ]
    du_doan_score: float = Field(ge=0, le=100)
    thuc_te_score: float = Field(ge=0, le=100)
    prediction_id: int | None = Field(default=None, ge=1)
    ghi_chu: str = Field(default="", max_length=1000)
    scope: Literal["general", "daily", "weekly", "monthly"] = "general"
    scope_key: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_birth_date_string(self) -> "FeedbackInput":
        try:
            day, month, year = (int(part) for part in self.ngay_sinh.split("/"))
            parsed = date(year, month, day)
        except (ValueError, TypeError) as exc:
            raise ValueError("Ngày sinh phải có định dạng DD/MM/YYYY hợp lệ.") from exc
        self.ngay_sinh = parsed.strftime("%d/%m/%Y")
        return self


class UserPreferencesInput(BaseModel):
    training_consent: bool
    notifications_enabled: bool
    analysis_notifications_enabled: bool = False


class TuViInput(BaseModel):
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)
    gio: int = Field(default=0, ge=0, le=23)
    luu: bool = True
    luan_giai: bool = False

    @model_validator(mode="after")
    def validate_calendar_date(self) -> "TuViInput":
        try:
            date(self.nam, self.thang, self.ngay)
        except ValueError as exc:
            raise ValueError("Ngày sinh không hợp lệ.") from exc
        return self


class TarotInput(BaseModel):
    cau_hoi: str = Field(min_length=5, max_length=500)
    so_la: Literal[1, 3, 5] = 3

    @model_validator(mode="after")
    def trim_question(self) -> "TarotInput":
        self.cau_hoi = self.cau_hoi.strip()
        if len(self.cau_hoi) < 5:
            raise ValueError("Câu hỏi cần có từ 5 đến 500 ký tự.")
        return self


class KinhDichInput(BaseModel):
    cau_hoi: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def trim_question(self) -> "KinhDichInput":
        self.cau_hoi = self.cau_hoi.strip()
        if len(self.cau_hoi) < 5:
            raise ValueError("Câu hỏi cần có từ 5 đến 500 ký tự.")
        return self


class BirthPairInput(BaseModel):
    ngay_sinh_a: date
    ngay_sinh_b: date


class ShareInput(BaseModel):
    ngay_sinh: date
    include_chart: bool = False
    expires_in_days: int = Field(default=30, ge=1, le=90)


class ABWeightInput(BaseModel):
    task: Literal["analyze"]
    weights: dict[str, float]


class FengShuiInput(BaseModel):
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

    @model_validator(mode="after")
    def validate_inputs(self) -> "FengShuiInput":
        try:
            date(self.nam, self.thang, self.ngay)
        except ValueError as exc:
            raise ValueError("Ngày sinh không hợp lệ.") from exc
        for direction in (self.huong_nha, self.huong_bep, self.huong_phong_ngu):
            if direction is not None and direction not in HUONG:
                raise ValueError(f"Hướng phải là một trong: {', '.join(HUONG)}.")
        return self


class PersonalEventInput(BaseModel):
    loai: str
    ngay: date
    ghi_chu: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_event(self) -> "PersonalEventInput":
        if self.loai not in EVENTS:
            raise ValueError("Loại sự kiện không được hỗ trợ.")
        self.ghi_chu = self.ghi_chu.strip()
        return self


class EnvironmentInput(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class CombinedInput(FengShuiInput):
    ngay_bat_dau: date | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "CombinedInput":
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Cần nhập đồng thời vĩ độ và kinh độ.")
        return self


@app.get("/")
def login_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html", media_type="text/html")


@app.get("/login")
def login_alias() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html", media_type="text/html")


@app.get("/app")
def app_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.html", media_type="text/html")


@app.get("/tu-vi")
@app.get("/tuvu")
def tu_vi_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "tuvu.html", media_type="text/html")


@app.get("/hop-tuoi")
def compatibility_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "hop-tuoi.html", media_type="text/html")


@app.get("/tarot")
def tarot_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "tarot.html", media_type="text/html")


@app.get("/kinh-dich")
def kinh_dich_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "kinh-dich.html", media_type="text/html")


@app.get("/phong-thuy")
def phong_thuy_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "phong-thuy.html", media_type="text/html")


@app.get("/su-kien")
def su_kien_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "su-kien.html", media_type="text/html")


@app.get("/timeline-vi-mo")
def timeline_vi_mo_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "timeline-vi-mo.html", media_type="text/html")


@app.get("/share/{token}")
def share_page(token: str = ApiPath(min_length=20, max_length=100)) -> FileResponse:
    del token
    return FileResponse(
        FRONTEND_DIR / "share.html",
        media_type="text/html",
        headers={"Cache-Control": "private, no-store"},
    )


@app.get("/offline.html")
def offline_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "offline.html", media_type="text/html")


@app.get("/manifest.json")
def pwa_manifest() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/icon.svg")
def pwa_icon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "icon.svg", media_type="image/svg+xml")


@app.get("/health")
async def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "checks": {"api": "ok", "db": "error"}},
        ) from exc
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.0)) as client:
            response = await client.get(f"{ollama.base_url}/api/tags")
        ollama_status = "ok" if response.status_code == 200 else "degraded"
    except httpx.RequestError:
        ollama_status = "unreachable"
    return {
        "status": "healthy",
        "checks": {"api": "ok", "db": "ok", "ollama": ollama_status},
        "version": app.version,
    }


@app.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    user = User(
        username=data.username,
        email=str(data.email),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username hoặc email đã được đăng ký.",
        ) from exc
    return user


@app.post("/api/auth/login")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    user = db.query(User).filter(User.username == form.username.lower()).first()
    if user is None or not user.is_active or not verify_password(
        form.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai username hoặc password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = create_access_token({"sub": str(user.id)})
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
        },
    }


@app.get("/api/auth/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@app.get("/api/auth/preferences")
def get_preferences(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    return {
        "training_consent": user.training_consent,
        "notifications_enabled": user.notifications_enabled,
        "analysis_notifications_enabled": user.analysis_notifications_enabled,
        "telegram_linked": user.telegram_chat_id is not None,
    }


@app.put("/api/auth/preferences")
def update_preferences(
    data: UserPreferencesInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    if data.analysis_notifications_enabled and user.telegram_chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hãy liên kết Telegram trước khi bật gửi kết quả diễn giải.",
        )
    if user.training_consent and not data.training_consent:
        profile_ids = [
            row[0] for row in db.query(Profile.id).filter_by(user_id=user.id).all()
        ]
        if profile_ids:
            (
                db.query(EventFeedback)
                .filter(EventFeedback.profile_id.in_(profile_ids))
                .update(
                    {EventFeedback.training_approved: False},
                    synchronize_session=False,
                )
            )
    user.training_consent = data.training_consent
    user.notifications_enabled = data.notifications_enabled
    user.analysis_notifications_enabled = data.analysis_notifications_enabled
    db.commit()
    return {
        "training_consent": user.training_consent,
        "notifications_enabled": user.notifications_enabled,
        "analysis_notifications_enabled": user.analysis_notifications_enabled,
        "telegram_linked": user.telegram_chat_id is not None,
    }


@app.post("/api/telegram/link-code")
def create_telegram_link_code(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot chưa được cấu hình trên máy chủ.",
        )
    code = secrets.token_urlsafe(24)
    expires_at = utcnow_naive() + timedelta(minutes=10)
    db.query(TelegramLinkChallenge).filter(
        TelegramLinkChallenge.user_id == user.id,
        TelegramLinkChallenge.used_at.is_(None),
    ).delete(synchronize_session=False)
    db.add(
        TelegramLinkChallenge(
            user_id=user.id,
            code_digest=hashlib.sha256(code.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
    )
    db.commit()
    return {"code": code, "expires_at": expires_at.isoformat()}


@app.get("/api/profiles")
def list_saved_profiles(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, list[dict[str, Any]]]:
    profiles = (
        db.query(Profile)
        .filter_by(user_id=user.id)
        .order_by(Profile.created_at.desc(), Profile.id.desc())
        .limit(100)
        .all()
    )
    profile_ids = [profile.id for profile in profiles]
    latest_predictions: dict[int, Prediction] = {}
    if profile_ids:
        predictions = (
            db.query(Prediction)
            .filter(Prediction.profile_id.in_(profile_ids))
            .order_by(Prediction.created_at.desc(), Prediction.id.desc())
            .all()
        )
        for prediction in predictions:
            latest_predictions.setdefault(prediction.profile_id, prediction)

    items = []
    for profile in profiles:
        latest = latest_predictions.get(profile.id)
        items.append({
            "id": profile.id,
            "profile": json.loads(profile.profile_json),
            "latest_prediction": (
                {
                    "prediction_id": latest.id,
                    "chi_so": json.loads(latest.chi_so_json),
                    "phan_tich": json.loads(latest.du_doan_json),
                    "created_at": latest.created_at.isoformat(),
                }
                if latest is not None
                else None
            ),
        })
    return {"items": items}


@app.post("/api/phong-thuy/phan-tich")
def api_phong_thuy(
    data: FengShuiInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        result = phan_tich_toan_dien(
            data.ngay, data.thang, data.nam,
            gioi_tinh=data.gioi_tinh,
            huong_nha=data.huong_nha,
            huong_bep=data.huong_bep,
            huong_phong_ngu=data.huong_phong_ngu,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["huong_theo_muc_dich"] = [
        item for item in result["huong_tot"]
        if item["cung"] in HUONG_THEO_MUC_DICH[data.muc_dich]
    ]
    return result


@app.post("/api/phong-thuy/llm-tu-van")
async def api_phong_thuy_llm(
    data: FengShuiInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        measurements = phan_tich_toan_dien(
            data.ngay, data.thang, data.nam, data.gioi_tinh,
            data.huong_nha, data.huong_bep, data.huong_phong_ngu,
        )
        prompt = f"""Diễn giải thông tin phong thủy dưới đây như nội dung văn hóa tham khảo.
Không khẳng định nhân quả hoặc dự đoán tương lai. Chỉ đưa gợi ý bố trí an toàn,
tự nguyện, ít tốn kém và không cần cải tạo kết cấu. Không đưa lời khuyên y tế,
pháp lý hay đầu tư. Trả về duy nhất JSON có các trường:
{{"danh_gia_tong_quan":"...", "diem_tham_khao":["..."],
"bo_tri_thuc_te":["..."], "canh_bao":["..."]}}

Dữ liệu: {json.dumps(measurements, ensure_ascii=False)}
"""
        raw = await ollama.generate(
            prompt,
            system="Bạn là trợ lý văn hóa có trách nhiệm; không trình bày niềm tin như sự thật khoa học.",
            temperature=0.4,
            json_mode=True,
        )
        advice = _parse_llm_json(raw)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc
    return {"so_lieu": measurements, "tu_van_llm": advice}


@app.get("/api/phong-thuy/phi-tinh")
def api_phi_tinh(
    _user: Annotated[User, Depends(get_current_user)],
    ngay: date | None = None,
) -> dict[str, Any]:
    del _user
    return phi_tinh_ngay(ngay or date.today())


@app.get("/api/su-kien/danh-muc")
def api_danh_muc_su_kien(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return danh_muc_su_kien()


@app.get("/api/su-kien")
def api_list_su_kien(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
) -> dict[str, Any]:
    query = db.query(SavedEvent).filter(SavedEvent.user_id == user.id)
    if tu_ngay:
        query = query.filter(SavedEvent.ngay >= tu_ngay.isoformat())
    if den_ngay:
        query = query.filter(SavedEvent.ngay <= den_ngay.isoformat())
    events = query.order_by(SavedEvent.ngay.asc(), SavedEvent.id.asc()).limit(500).all()
    return {"items": [
        {
            "id": item.id,
            "loai": item.loai,
            "ten": EVENTS[item.loai]["ten"],
            "ngay": item.ngay,
            "ghi_chu": item.ghi_chu,
        }
        for item in events
    ]}


@app.post("/api/su-kien", status_code=status.HTTP_201_CREATED)
def api_create_su_kien(
    data: PersonalEventInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    event = SavedEvent(
        user_id=user.id,
        loai=data.loai,
        ngay=data.ngay.isoformat(),
        ghi_chu=data.ghi_chu,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "loai": event.loai, "ngay": event.ngay, "ghi_chu": event.ghi_chu}


@app.delete("/api/su-kien/{event_id}")
def api_delete_su_kien(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    event_id: int = ApiPath(ge=1),
) -> dict[str, str]:
    event = db.query(SavedEvent).filter_by(id=event_id, user_id=user.id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự kiện.")
    db.delete(event)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/su-kien/tuan")
def api_su_kien_tuan(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    bat_dau: date | None = None,
) -> dict[str, Any]:
    start = bat_dau or date.today()
    stop = start + timedelta(days=6)
    events = db.query(SavedEvent).filter(
        SavedEvent.user_id == user.id,
        SavedEvent.ngay >= start.isoformat(),
        SavedEvent.ngay <= stop.isoformat(),
    ).order_by(SavedEvent.ngay.asc()).all()
    return quet_su_kien_tuan(
        [{"id": item.id, "loai": item.loai, "ngay": item.ngay, "note": item.ghi_chu} for item in events],
        start,
    )


@app.get("/api/su-kien/dai-han")
def api_su_kien_dai_han(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    nam: int | None = Query(default=None, ge=1900, le=2100),
) -> dict[str, Any]:
    year = nam or date.today().year
    events = db.query(SavedEvent).filter(
        SavedEvent.user_id == user.id,
        SavedEvent.ngay >= f"{year:04d}-01-01",
        SavedEvent.ngay <= f"{year:04d}-12-31",
    ).order_by(SavedEvent.ngay.asc()).limit(500).all()
    return du_bao_dai_han(
        [{"loai": item.loai, "ngay": item.ngay, "note": item.ghi_chu} for item in events],
        year,
    )


@app.get("/api/vi-mo/timeline")
def api_timeline_vi_mo(
    user: Annotated[User, Depends(get_current_user)],
    bat_dau: date | None = None,
    so_ngay: int = Query(default=90, ge=1, le=366),
) -> dict[str, Any]:
    del user
    return timeline_vi_mo(bat_dau, so_ngay)


@app.post("/api/moi-truong/hien-tai")
async def api_moi_truong_hien_tai(
    data: EnvironmentInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    if not os.getenv("OPENWEATHER_API_KEY", "").strip():
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ môi trường chưa được cấu hình. Tọa độ chưa được gửi đi.",
        )
    try:
        data_result = await lay_du_lieu_moi_truong(data.lat, data.lon)
    except WeatherProviderError as exc:
        logger.warning("Weather provider request failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    data_result["danh_gia"] = danh_gia_anh_huong_moi_truong(data_result)
    return data_result


@app.post("/api/tong-the")
async def api_tong_the(
    data: CombinedInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        phong_thuy = phan_tich_toan_dien(
            data.ngay, data.thang, data.nam, data.gioi_tinh,
            data.huong_nha, data.huong_bep, data.huong_phong_ngu,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = data.ngay_bat_dau or date.today()
    end = start + timedelta(days=6)
    events = db.query(SavedEvent).filter(
        SavedEvent.user_id == user.id,
        SavedEvent.ngay >= start.isoformat(),
        SavedEvent.ngay <= end.isoformat(),
    ).order_by(SavedEvent.ngay.asc()).all()
    event_summary = quet_su_kien_tuan(
        [{"id": item.id, "loai": item.loai, "ngay": item.ngay, "note": item.ghi_chu} for item in events],
        start,
    )
    profile = phan_tich_ngay_sinh(data.ngay, data.thang, data.nam)
    if data.lat is not None and data.lon is not None:
        if not os.getenv("OPENWEATHER_API_KEY", "").strip():
            raise HTTPException(
                status_code=503,
                detail="Dịch vụ môi trường chưa được cấu hình. Tọa độ chưa được gửi đi.",
            )
        try:
            environment = await lay_du_lieu_moi_truong(data.lat, data.lon)
        except WeatherProviderError as exc:
            logger.warning("Weather provider request failed: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        environment["danh_gia"] = danh_gia_anh_huong_moi_truong(environment)
    else:
        environment = None
    return {
        "phong_thuy": phong_thuy,
        "su_kien": event_summary,
        "moi_truong": environment,
        "vi_mo": timeline_vi_mo(start, 90),
        "tong_hop": buc_tranh_tong_the(profile, phong_thuy, event_summary, environment),
    }


def _prepare_analysis(
    data: BirthInput, user: User, db: Session
) -> tuple[
    Profile, dict[str, Any], dict[str, float], dict[str, float], list[dict[str, Any]]
]:
    profile_data = phan_tich_ngay_sinh(data.ngay, data.thang, data.nam)
    profile_data["ho_ten"] = data.ho_ten.strip()
    db_profile = (
        db.query(Profile)
        .filter_by(user_id=user.id, ngay_sinh=profile_data["ngay_sinh"])
        .first()
    )
    if db_profile is None:
        db_profile = Profile(
            user_id=user.id,
            ngay_sinh=profile_data["ngay_sinh"],
            ho_ten=profile_data["ho_ten"],
            profile_json=json.dumps(profile_data, ensure_ascii=False),
        )
        db.add(db_profile)
    else:
        profile_data["ho_ten"] = profile_data["ho_ten"] or db_profile.ho_ten or ""
        db_profile.ho_ten = profile_data["ho_ten"]
        db_profile.profile_json = json.dumps(profile_data, ensure_ascii=False)
    db.commit()
    db.refresh(db_profile)

    weights = get_weights_from_history(db, [db_profile.id])
    adjusted_scores = apply_experimental_weights(
        tinh_chi_so_su_kien(profile_data), weights
    )
    rows = (
        db.query(EventFeedback)
        .filter_by(profile_id=db_profile.id)
        .order_by(EventFeedback.created_at.desc())
        .limit(20)
        .all()
    )
    history_data = [
        {
            "loai_su_kien": row.loai_su_kien,
            "du_doan_score": row.du_doan_score,
            "thuc_te_score": row.thuc_te_score,
            "ghi_chu": row.ghi_chu,
        }
        for row in rows
    ]
    return db_profile, profile_data, adjusted_scores, weights, history_data


@app.post("/api/analyze")
async def analyze(
    data: BirthInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    db_profile, profile_data, adjusted_scores, weights, history_data = (
        _prepare_analysis(data, user, db)
    )
    try:
        result = await ollama.phan_tich_va_hanh_dong(
            profile_data, adjusted_scores, history_data
        )
    except (httpx.HTTPError, ValueError) as exc:
        db.rollback()
        raise _ollama_http_error(exc) from exc

    prediction = Prediction(
        profile_id=db_profile.id,
        scope="general",
        chi_so_json=json.dumps(adjusted_scores, ensure_ascii=False),
        du_doan_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(prediction)
    db.commit()
    return {
        "profile": profile_data,
        "chi_so": adjusted_scores,
        "trong_so_hoc": weights,
        "phan_tich": result,
        "prediction_id": prediction.id,
        "so_lan_da_xem": db.query(Prediction).filter_by(profile_id=db_profile.id).count(),
        "ghi_chu_chi_so": "Chỉ số và hệ số là quy tắc tham khảo, không phải xác suất.",
    }


@app.post("/api/analyze/stream")
async def analyze_stream(
    data: BirthInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    db_profile, profile_data, adjusted_scores, weights, history_data = (
        _prepare_analysis(data, user, db)
    )
    system, prompt = build_analysis_prompt(profile_data, adjusted_scores, history_data)

    def encode_event(name: str, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return f"event: {name}\ndata: {body}\n\n"

    async def event_stream():
        yield encode_event(
            "metadata",
            {
                "profile": profile_data,
                "chi_so": adjusted_scores,
                "trong_so_hoc": weights,
            },
        )
        generated: list[str] = []
        generated_length = 0
        stream_finished = False
        try:
            async for chunk in ollama.generate_stream(
                prompt, system=system, temperature=0.6, json_mode=True
            ):
                token_text = chunk["token"]
                generated_length += len(token_text)
                if generated_length > 250_000:
                    raise ValueError("Ollama stream vượt quá giới hạn độ dài.")
                generated.append(token_text)
                yield encode_event("token", chunk)
                stream_finished = chunk["done"]
        except httpx.HTTPError:
            yield encode_event(
                "error", {"message": "Không thể kết nối hoặc đọc stream từ Ollama."}
            )
            return
        except ValueError as exc:
            yield encode_event("error", {"message": str(exc)})
            return
        if not stream_finished:
            yield encode_event(
                "error", {"message": "Ollama kết thúc stream trước khi hoàn tất."}
            )
            return

        try:
            result = _parse_llm_json("".join(generated))
            prediction = Prediction(
                profile_id=db_profile.id,
                scope="general",
                chi_so_json=json.dumps(adjusted_scores, ensure_ascii=False),
                du_doan_json=json.dumps(result, ensure_ascii=False),
            )
            db.add(prediction)
            db.commit()
        except ValueError as exc:
            db.rollback()
            yield encode_event("error", {"message": str(exc)})
            return
        except SQLAlchemyError:
            db.rollback()
            yield encode_event(
                "error", {"message": "Không thể lưu kết quả phân tích vào cơ sở dữ liệu."}
            )
            return
        notification_status = "not_enabled"
        if user.analysis_notifications_enabled and user.telegram_chat_id is not None:
            try:
                from notifications import telegram

                attachment = json.dumps(
                    {"profile": profile_data, "phan_tich": result},
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
                await telegram.send_document(
                    user.telegram_chat_id,
                    f"phan-tich-{prediction.id}.json",
                    attachment,
                    "Kết quả diễn giải đã hoàn tất. Tệp đính kèm gồm hồ sơ và toàn bộ nội dung.",
                )
                notification_status = "sent"
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "Telegram analysis delivery failed for user %s (%s).",
                    user.id,
                    type(exc).__name__,
                )
                notification_status = "failed"
        yield encode_event(
            "done",
            {
                "parsed": result,
                "prediction_id": prediction.id,
                "telegram_notification": notification_status,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/feedback")
def feedback(
    data: FeedbackInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id, ngay_sinh=data.ngay_sinh)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ của tài khoản này.")
    if data.prediction_id is not None:
        prediction = (
            db.query(Prediction)
            .filter_by(id=data.prediction_id, profile_id=profile.id)
            .first()
        )
        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy dự đoán tương ứng với hồ sơ này.",
            )
        if prediction.scope != data.scope or prediction.scope_key != data.scope_key:
            raise HTTPException(
                status_code=422,
                detail="Scope của feedback phải khớp với dự đoán được liên kết.",
            )
    feedback_row = EventFeedback(
        profile_id=profile.id,
        prediction_id=data.prediction_id,
        loai_su_kien=data.loai_su_kien,
        du_doan_score=data.du_doan_score,
        thuc_te_score=data.thuc_te_score,
        ghi_chu=data.ghi_chu.strip(),
        scope=data.scope,
        scope_key=data.scope_key,
    )
    db.add(feedback_row)
    db.flush()
    record_feedback_reward(db, feedback_row, profile)
    db.commit()
    return {"ok": True}


@app.post("/api/relearn/{ngay_sinh:path}")
async def relearn(
    ngay_sinh: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    rows = (
        db.query(EventFeedback)
        .filter_by(profile_id=profile.id)
        .order_by(EventFeedback.created_at.asc())
        .all()
    )
    if len(rows) < 3:
        return {"message": "Cần ít nhất 3 phản hồi để phân tích.", "so_feedback": len(rows)}
    feedback_data = [
        {
            "loai_su_kien": row.loai_su_kien,
            "du_doan": row.du_doan_score,
            "thuc_te": row.thuc_te_score,
            "chenh_lech": row.thuc_te_score - row.du_doan_score,
        }
        for row in rows
    ]
    try:
        result = await ollama.hieu_chinh_tu_feedback(feedback_data)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc
    return {
        "so_feedback": len(rows),
        "dieu_chinh": result,
        "ghi_chu": "Đây là phân tích feedback, không phải huấn luyện lại model.",
    }


@app.get("/api/history/{ngay_sinh:path}")
def history(
    ngay_sinh: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id, ngay_sinh=ngay_sinh)
        .first()
    )
    if profile is None:
        return {"items": []}
    rows = (
        db.query(EventFeedback)
        .filter_by(profile_id=profile.id)
        .order_by(EventFeedback.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "loai_su_kien": row.loai_su_kien,
                "du_doan": row.du_doan_score,
                "thuc_te": row.thuc_te_score,
                "chenh_lech": row.thuc_te_score - row.du_doan_score,
                "ghi_chu": row.ghi_chu,
                "scope": row.scope,
                "ngay": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@app.get("/api/lich-van-nien/ngay")
def api_day(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    d: date | None = Query(default=None, description="YYYY-MM-DD"),
    ngay_sinh: str | None = Query(default=None),
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    birth_profile = json.loads(profile.profile_json)
    return phan_tich_ngay(d or date.today(), birth_profile["menh_nap_am"], birth_profile["con_giap"])


@app.get("/api/lich-van-nien/tuan")
def api_week(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    start: date | None = Query(default=None),
    ngay_sinh: str | None = Query(default=None),
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    birth_profile = json.loads(profile.profile_json)
    data = du_doan_tuan(
        birth_profile["menh_nap_am"], birth_profile["con_giap"], start
    )
    return tong_hop_tuan(data)


@app.get("/api/lich-van-nien/thang")
def api_month(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    year: int = Query(ge=1900, le=2100),
    month: int = Query(ge=1, le=12),
    ngay_sinh: str | None = Query(default=None),
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    birth_profile = json.loads(profile.profile_json)
    days = du_doan_thang(
        birth_profile["menh_nap_am"], birth_profile["con_giap"], year, month
    )
    return tong_hop_thang(days)


@app.post("/api/lich-van-nien/llm-tuan")
async def api_llm_week(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    start: date | None = Query(default=None),
    ngay_sinh: str | None = Query(default=None),
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    birth_profile = json.loads(profile.profile_json)
    weekly_summary = tong_hop_tuan(
        du_doan_tuan(
            birth_profile["menh_nap_am"], birth_profile["con_giap"], start
        )
    )
    prompt = f"""Dữ liệu lịch tuần sau chỉ là hệ thống quy tắc truyền thống giản lược,
không phải dự đoán xác suất hoặc khuyến nghị chuyên môn.
Hồ sơ: mệnh {birth_profile['menh_nap_am']}, con giáp {birth_profile['con_giap']}.
Dữ liệu tuần: {json.dumps(weekly_summary, ensure_ascii=False)}
Trả về object JSON với tom_tat_tuan (string), lich_hanh_dong (array các mục có
ngay, viec_nen_lam, viec_nen_tranh, gio_tot), loi_khuyen_tuan (string).
Gợi ý phải an toàn, không đưa tư vấn y tế, pháp lý hay tài chính."""
    try:
        raw = await ollama.generate(prompt, temperature=0.5, json_mode=True)
        result = _parse_llm_json(raw)
        actions = result.get("lich_hanh_dong", [])
        if not isinstance(actions, list) or any(
            not isinstance(item, dict) for item in actions
        ):
            raise ValueError("Ollama trả về danh sách lịch tuần không hợp lệ.")
        for item in actions:
            item["viec_nen_lam"] = _normalize_weekly_text_list(
                item.get("viec_nen_lam")
            )
            item["viec_nen_tranh"] = _normalize_weekly_text_list(
                item.get("viec_nen_tranh")
            )
        return {
            **result,
            "du_lieu_tuan": weekly_summary,
            "ghi_chu": "Nội dung do AI tạo để tham khảo, có thể không chính xác.",
        }
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@app.post("/api/tu-vi/lap-so")
def api_tu_vi(
    data: TuViInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        chart = lap_la_so(data.ngay, data.thang, data.nam, data.gio)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    birth_date = f"{data.ngay:02d}/{data.thang:02d}/{data.nam}"
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id, ngay_sinh=birth_date)
        .first()
    )
    if profile is not None and data.luu:
        profile.tu_vi_json = json.dumps(chart, ensure_ascii=False)
        db.commit()
    return chart


async def _interpret_chart(chart: dict[str, Any]) -> dict[str, Any]:
    compact_chart = {
        "am_lich": chart["am_lich"],
        "can_chi_nam": chart["can_chi_nam"],
        "cuc": chart["cuc"],
        "menh": chart["menh_chi"],
        "than": chart["than_chi"],
        "cung": [
            {
                "ten": palace["cung"],
                "dia_chi": palace["dia_chi"],
                "chinh_tinh": palace["chinh_tinh"],
                "phu_tinh": palace["phu_tinh"][:6],
                "la_menh": palace["la_menh"],
                "la_than": palace["la_than"],
            }
            for palace in chart["cung"]
        ],
    }
    prompt = f"""Lá số dưới đây được tạo bằng thuật toán Tử Vi giản lược, có thể khác
các trường phái. Hãy diễn giải như nội dung văn hóa/giải trí, không khẳng định tương
lai, không đưa quyết định y tế, pháp lý, tài chính.
{json.dumps(compact_chart, ensure_ascii=False)}
Chỉ trả JSON object: tong_quan (string), diem_manh (array), diem_can_luu_y (array),
cac_cung_noi_bat (array gồm cung, luan_giai, hanh_dong), loi_khuyen_tong_the (string)."""
    try:
        raw = await ollama.generate(prompt, temperature=0.5, json_mode=True)
        return _parse_llm_json(raw)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@app.post("/api/tu-vi/luan-giai")
async def api_tu_vi_interpretation(
    data: TuViInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        chart = lap_la_so(data.ngay, data.thang, data.nam, data.gio)
        interpretation = await _interpret_chart(chart)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"la_so": chart, "luan_giai": interpretation}


@app.post("/api/tu-vi/export-pdf")
async def export_tu_vi_pdf(
    data: TuViInput,
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        chart = lap_la_so(data.ngay, data.thang, data.nam, data.gio)
        interpretation = await _interpret_chart(chart) if data.luan_giai else None
        pdf_bytes = export_la_so_pdf(
            chart,
            interpretation,
            user_name=user.full_name or user.username,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="la-so-{data.ngay:02d}'
                f'{data.thang:02d}{data.nam}.pdf"'
            ),
            "Cache-Control": "private, no-store",
        },
    )


@app.post("/api/analyze/export-pdf")
async def export_ban_menh_pdf_endpoint(
    data: BirthInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _, profile, scores, _, history = _prepare_analysis(data, user, db)
    try:
        analysis = await ollama.phan_tich_va_hanh_dong(profile, scores, history)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc
    try:
        pdf_bytes = export_ban_menh_pdf(
            profile, scores, analysis, user_name=user.full_name or user.username
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="ban-menh.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@app.post("/api/hop-tuoi")
def api_compatibility(
    data: BirthPairInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return compatibility(
        data.ngay_sinh_a.day, data.ngay_sinh_a.month, data.ngay_sinh_a.year,
        data.ngay_sinh_b.day, data.ngay_sinh_b.month, data.ngay_sinh_b.year,
    )


@app.post("/api/tarot")
async def api_tarot(
    data: TarotInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        return await luan_giai_tarot(data.cau_hoi, data.so_la)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@app.post("/api/kinh-dich")
async def api_kinh_dich(
    data: KinhDichInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        return await luan_giai_que(data.cau_hoi)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@app.post("/api/share")
def create_share(
    data: ShareInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    birth_string = data.ngay_sinh.strftime("%d/%m/%Y")
    profile_row = (
        db.query(Profile)
        .filter_by(user_id=user.id, ngay_sinh=birth_string)
        .first()
    )
    if profile_row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ của tài khoản này.")
    profile = json.loads(profile_row.profile_json)
    payload: dict[str, Any] = {
        "menh_nap_am": profile.get("menh_nap_am"),
        "can_chi_nam": profile.get("can_chi_nam"),
        "con_giap": profile.get("con_giap"),
        "so_chu_dao": profile.get("so_chu_dao"),
        "cung_phi": profile.get("cung_phi"),
        "ghi_chu": "Thông tin đã lược bỏ tên và ngày sinh.",
    }
    if data.include_chart:
        if not profile_row.tu_vi_json:
            raise HTTPException(
                status_code=409,
                detail="Hãy lưu lá số Tử Vi trước khi thêm vào liên kết chia sẻ.",
            )
        chart = json.loads(profile_row.tu_vi_json)
        payload["la_so"] = {
            "can_chi_nam": chart["can_chi_nam"],
            "cuc": chart["cuc"],
            "menh_chi": chart["menh_chi"],
            "than_chi": chart["than_chi"],
            "tu_vi_tai": chart["tu_vi_tai"],
            "cung": [
                {
                    "cung": palace["cung"],
                    "dia_chi": palace["dia_chi"],
                    "la_menh": palace["la_menh"],
                    "la_than": palace["la_than"],
                    "chinh_tinh": palace["chinh_tinh"],
                    "phu_tinh": palace["phu_tinh"][:6],
                }
                for palace in chart["cung"]
            ],
        }
    token, row = create_share_link(db, user.id, payload, data.expires_in_days)
    return {
        "url": f"/share/{token}",
        "expires_at": row.expires_at.isoformat(),
        "share_id": row.id,
    }


@app.get("/api/share/{token}")
def read_share(
    response: Response,
    token: str = ApiPath(min_length=20, max_length=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "private, no-store"
    row = get_share_link(db, token)
    if row is None:
        raise HTTPException(status_code=404, detail="Liên kết không tồn tại hoặc đã hết hạn.")
    return {
        "profile": json.loads(row.payload_json),
        "expires_at": row.expires_at.isoformat(),
    }


@app.delete("/api/share/{token}")
def delete_share(
    token: str = ApiPath(min_length=20, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if not revoke_share_link(db, user.id, token):
        raise HTTPException(status_code=404, detail="Liên kết không tồn tại.")
    return {"revoked": True}


def _require_ab_admin(user: User) -> None:
    admins = {
        value.strip()
        for value in os.getenv("ADMIN_USER_IDS", "").split(",")
        if value.strip().isdigit()
    }
    if str(user.id) not in admins:
        raise HTTPException(status_code=403, detail="Cần quyền quản trị A/B.")


@app.post("/api/analyze/ab")
async def analyze_ab(
    data: BirthInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    task = "analyze"
    variant = assign_variant(db, user.id, task)
    db_profile, profile, scores, weights, history = _prepare_analysis(data, user, db)
    system, prompt = build_analysis_prompt(profile, scores, history)
    if variant == "treatment":
        system += " Ưu tiên gợi ý nhỏ, cụ thể, có thể tự nguyện thử và tự đánh giá."
    started = time.perf_counter()
    try:
        raw = await ollama.generate(prompt, system=system, temperature=0.6, json_mode=True)
        result = _parse_llm_json(raw)
    except (httpx.HTTPError, ValueError) as exc:
        record_experiment(
            db, user.id, None, task, variant,
            round((time.perf_counter() - started) * 1000), False,
        )
        raise _ollama_http_error(exc) from exc
    prediction = Prediction(
        profile_id=db_profile.id,
        scope="general",
        chi_so_json=json.dumps(scores, ensure_ascii=False),
        du_doan_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    experiment = record_experiment(
        db,
        user.id,
        prediction.id,
        task,
        variant,
        round((time.perf_counter() - started) * 1000),
        True,
    )
    return {
        "profile": profile,
        "chi_so": scores,
        "trong_so_hoc": weights,
        "phan_tich": result,
        "prediction_id": prediction.id,
        "experiment_id": experiment.id,
        "variant": variant,
        "ghi_chu": "Kết quả A/B là thử nghiệm nội bộ, không phải xác nhận độ chính xác.",
    }


@app.get("/api/ab/overview")
def ab_overview(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return experiment_metrics(db, user.id)


@app.get("/api/admin/ab/overview")
def admin_ab_overview(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    _require_ab_admin(user)
    return experiment_metrics(db)


@app.put("/api/admin/ab/weights")
def admin_ab_weights(
    data: ABWeightInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    _require_ab_admin(user)
    if (
        set(data.weights) != {"control", "treatment"}
        or any(
            not math.isfinite(value)
            or value < 0
            for value in data.weights.values()
        )
        or sum(data.weights.values()) <= 0
    ):
        raise HTTPException(status_code=422, detail="Trọng số A/B không hợp lệ.")
    total = sum(data.weights.values())
    normalized = {key: value / total for key, value in data.weights.items()}
    update_weights(db, data.task, normalized)
    return {"task": data.task, "weights": normalized}


@app.get("/api/dashboard/overview")
def dashboard_overview(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(default=90, ge=1, le=3650),
) -> dict[str, Any]:
    profile_ids = [
        profile.id for profile in db.query(Profile).filter_by(user_id=user.id).all()
    ]
    if not profile_ids:
        return {"message": "Chưa có hồ sơ nào."}
    return {
        "by_field": accuracy_by_field(db, profile_ids, days),
        "timeline": accuracy_timeline(db, profile_ids, weeks=12),
        "bias": bias_analysis(db, profile_ids),
        "patterns": top_patterns(db, profile_ids),
        "weights": get_weights_from_history(db, profile_ids),
        "ghi_chu": "Chỉ số mô tả feedback do người dùng nhập, không phải độ chính xác khoa học.",
    }


@app.get("/api/dashboard/raw-feedback")
def dashboard_raw_feedback(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, list[dict[str, Any]]]:
    profile_ids = [
        profile.id for profile in db.query(Profile).filter_by(user_id=user.id).all()
    ]
    if not profile_ids:
        return {"items": []}
    rows = (
        db.query(EventFeedback)
        .filter(EventFeedback.profile_id.in_(profile_ids))
        .order_by(EventFeedback.created_at.asc())
        .limit(1000)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "loai": row.loai_su_kien,
                "du_doan": row.du_doan_score,
                "thuc_te": row.thuc_te_score,
                "scope": row.scope,
                "ngay": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }
