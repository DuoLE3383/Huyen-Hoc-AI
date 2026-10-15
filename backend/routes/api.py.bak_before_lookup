import hashlib
import json
import logging
import math
import os
import re
import secrets
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import text

from analytics.ab_testing import assign_variant, experiment_metrics, record_experiment, record_feedback_reward, update_weights
from analytics.analytics import (
    accuracy_by_field,
    accuracy_timeline,
    apply_experimental_weights,
    bias_analysis,
    get_weights_from_history,
    top_patterns,
)
from services.astrology import phan_tich_ngay_sinh, tinh_chi_so_su_kien
from core.auth import (
    UserOut,
    UserRegister,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from core.database import (
    EventFeedback,
    LocationHistory,
    Prediction,
    Profile,
    SavedEvent,
    TelegramLinkChallenge,
    User,
    get_db,
    init_db,
    SessionLocal,
    utcnow_naive,
)
from divination.lich_van_nien import (
    du_doan_thang,
    du_doan_tuan,
    phan_tich_ngay,
    tong_hop_thang,
    tong_hop_tuan,
)
from services.ollama_client import build_analysis_prompt, ollama
from services.pdf_export import export_ban_menh_pdf, export_la_so_pdf
from services.social import compatibility, create_share_link, get_share_link, revoke_share_link
from divination.tarot import luan_giai_tarot
from divination.kinh_dich import luan_giai_que, gieo_que, _build_que_info, _prompt_1_core, _prompt_2_tam_hop, _prompt_3_action, _clean_obj, _safe_parse
from divination.tu_vi import lap_la_so
from divination.phong_thuy import (
    HUONG,
    HUONG_THEO_MUC_DICH,
    phan_tich_toan_dien,
    phi_tinh_ngay,
)
from divination.su_kien import EVENTS, danh_muc_su_kien, du_bao_dai_han, quet_su_kien_tuan
from services.moi_truong import WeatherProviderError, danh_gia_anh_huong_moi_truong, lay_du_lieu_moi_truong
from services.vi_mo import timeline_vi_mo
from divination.ket_noi import buc_tranh_tong_the
from divination.ban_do_phong_thuy import lay_elevation, phan_tich_dia_hinh, tinh_phuong_vi_tu_toa_do
from divination.gia_dao import phan_tich_nhom_gia_dinh
from services.kinh_te_vi_mo import lay_du_lieu_thi_truong
from divination.trach_cat import ACTIVITIES as TRACH_CAT_ACTIVITIES, tim_ngay_dep
from divination.tam_linh import tao_thoi_khoa_tam_linh
from divination.tu_vi_tay_phuong import lap_natal_chart, so_sanh_dong_tay
from core.i18n import LANG_SUPPORTED, TRANSLATIONS, detect_lang
from services.narrative import stream_tong_the_narrative



logger = logging.getLogger(__name__)

router = APIRouter()


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
EVENT_TYPES = {"tai_van", "tinh_duyen", "su_nghiep", "suc_khoe", "gap_go", "thay_doi"}
SCOPE_TYPES = {"general", "daily", "weekly", "monthly"}
WEATHER_CACHE_TTL = timedelta(minutes=15)


async def _get_environment_for_user(
    lat: float, lon: float, user: User, db: Session
) -> dict[str, Any]:
    latitude_key = round(lat, 5)
    longitude_key = round(lon, 5)
    location = (
        db.query(LocationHistory)
        .filter(
            LocationHistory.user_id == user.id,
            LocationHistory.lat.between(latitude_key - 0.000005, latitude_key + 0.000005),
            LocationHistory.lon.between(longitude_key - 0.000005, longitude_key + 0.000005),
        )
        .order_by(LocationHistory.updated_at.desc(), LocationHistory.id.desc())
        .first()
    )
    now = utcnow_naive()
    reused = (
        location is not None
        and location.weather_json is not None
        and location.weather_fetched_at is not None
        and now - location.weather_fetched_at <= WEATHER_CACHE_TTL
    )
    if reused:
        environment = json.loads(location.weather_json)
        fetched_at = location.weather_fetched_at
    else:
        if not os.getenv("OPENWEATHER_API_KEY", "").strip():
            raise HTTPException(
                status_code=503,
                detail="Dịch vụ môi trường chưa được cấu hình. Tọa độ chưa được gửi đi.",
            )
        try:
            environment = await lay_du_lieu_moi_truong(lat, lon)
        except WeatherProviderError as exc:
            logger.warning("Weather provider request failed: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if location is None:
            location_key = f"coords:{latitude_key:.5f}:{longitude_key:.5f}"
            location = LocationHistory(
                user_id=user.id,
                address_key=location_key,
                address=f"Tọa độ {latitude_key:.5f}, {longitude_key:.5f}",
                formatted_address=f"Tọa độ {latitude_key:.5f}, {longitude_key:.5f}",
                lat=lat,
                lon=lon,
            )
            db.add(location)
        fetched_at = now
        location.weather_json = json.dumps(environment, ensure_ascii=False)
        location.weather_fetched_at = fetched_at
        db.commit()
        db.refresh(location)

    result = dict(environment)
    result["danh_gia"] = danh_gia_anh_huong_moi_truong(result)
    result["lich_su"] = {
        "tai_su_dung": reused,
        "thoi_diem_lay": fetched_at.isoformat(),
    }
    return result


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


_CJK_IDEOGRAPHS = re.compile(
    r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002FA1F]+"
)


def _clean_llm_strings(value: Any) -> Any:
    if isinstance(value, str):
        return _CJK_IDEOGRAPHS.sub("", value).strip()
    if isinstance(value, list):
        return [_clean_llm_strings(item) for item in value]
    if isinstance(value, dict):
        return {
            _CJK_IDEOGRAPHS.sub("", key).strip() if isinstance(key, str) else key:
            _clean_llm_strings(item)
            for key, item in value.items()
        }
    return value


def validate_and_clean_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Clean generated text, remove duplicate advice, and cap list sizes."""
    cleaned = _clean_llm_strings(analysis)

    for field in ("diem_manh", "diem_yeu", "canh_bao"):
        values = cleaned.get(field)
        if isinstance(values, list):
            unique_values = []
            seen = set()
            for item in values:
                if not isinstance(item, str):
                    continue
                normalized = item.casefold()
                if item and normalized not in seen:
                    seen.add(normalized)
                    unique_values.append(item)
            cleaned[field] = unique_values[:5]

    actions = cleaned.get("hanh_dong_cu_the")
    if isinstance(actions, list):
        unique_actions = []
        seen_actions = set()
        for action in actions:
            if not isinstance(action, dict):
                continue
            description = action.get("hanh_dong")
            if not isinstance(description, str) or not description:
                continue
            category = action.get("linh_vuc", "")
            key = (str(category).casefold(), description[:30].casefold())
            if key not in seen_actions:
                seen_actions.add(key)
                unique_actions.append(action)
        cleaned["hanh_dong_cu_the"] = unique_actions[:5]

    return cleaned


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


def _ollama_stream_error_message(exc: httpx.HTTPStatusError) -> str:
    try:
        error_data = exc.response.json()
    except ValueError:
        error_data = None
    detail = error_data.get("error") if isinstance(error_data, dict) else None
    if isinstance(detail, str) and detail.strip():
        return f"Ollama báo lỗi HTTP {exc.response.status_code}: {detail.strip()[:300]}"
    return f"Ollama báo lỗi HTTP {exc.response.status_code} khi nạp model."


class BirthInput(BaseModel):
    ho_ten: str = Field(default="", max_length=100)
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)
    gio_sinh: int | None = Field(default=None, ge=0, le=23)

    @model_validator(mode="after")
    def normalize_name(self) -> "BirthInput":
        self.ho_ten = self.ho_ten.strip()
        return self

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


class BatTuInput(BaseModel):
    ngay_sinh: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    gio_sinh: str = Field(pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    gioi_tinh: str = Field(pattern=r"^(nam|nu)$")
    noi_sinh: str | None = None


class KinhDichInput(BaseModel):
    cau_hoi: str = Field(min_length=5, max_length=500)
    # Bát tự BẮT BUỘC
    ngay_sinh: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    gio_sinh: str = Field(pattern=r"^\d{2}:\d{2}$")
    gioi_tinh: str = Field(pattern=r"^(nam|nu)$")
    noi_sinh: str | None = None

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


class MapAnalysisInput(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    huong_dat: Literal["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]
    truy_van_do_cao: bool = False


class HouseholdMemberInput(BaseModel):
    ten: str = Field(min_length=1, max_length=60)
    vai_tro: str = Field(min_length=1, max_length=32)
    ngay_sinh: date
    gioi_tinh: Literal["nam", "nu"]

    @model_validator(mode="after")
    def trim_text(self) -> "HouseholdMemberInput":
        self.ten = self.ten.strip()
        self.vai_tro = self.vai_tro.strip()
        if not self.ten or not self.vai_tro:
            raise ValueError("Tên và vai trò không được để trống.")
        return self


class HouseholdInput(BaseModel):
    thanh_vien: list[HouseholdMemberInput] = Field(min_length=1, max_length=10)


class TrachCatInput(BaseModel):
    loai_viec: Literal[
        "cuoi_hoi", "khai_truong", "ky_ket", "xuat_hanh", "dong_tho",
        "nhap_hoc", "giao_dich", "gap_go", "chuyen_nha",
    ]
    tu_ngay: date | None = None
    so_ngay_tim: int = Field(default=60, ge=1, le=90)
    so_ket_qua: int = Field(default=5, ge=1, le=20)


class WesternChartInput(BaseModel):
    ngay: int = Field(ge=1, le=31)
    thang: int = Field(ge=1, le=12)
    nam: int = Field(ge=1900, le=2100)

    @model_validator(mode="after")
    def validate_calendar_date(self) -> "WesternChartInput":
        try:
            date(self.nam, self.thang, self.ngay)
        except ValueError as exc:
            raise ValueError("Ngày sinh không hợp lệ.") from exc
        return self


@router.get("/")
def login_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html", media_type="text/html")


@router.get("/login")
def login_alias() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "login.html", media_type="text/html")


@router.get("/app")
def app_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


@router.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "dashboard.html", media_type="text/html")


@router.get("/tu-vi")
@router.get("/tuvu")
def tu_vi_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "tuvu.html", media_type="text/html")


@router.get("/hop-tuoi")
def compatibility_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "hop-tuoi.html", media_type="text/html")


@router.get("/tarot")
def tarot_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "tarot.html", media_type="text/html")


@router.get("/kinh-dich")
def kinh_dich_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "kinh-dich.html", media_type="text/html")


@router.get("/phong-thuy")
def phong_thuy_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "phong-thuy.html", media_type="text/html")


@router.get("/su-kien")
def su_kien_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "su-kien.html", media_type="text/html")


@router.get("/timeline-vi-mo")
def timeline_vi_mo_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "timeline-vi-mo.html", media_type="text/html")


@router.get("/ban-do")
def ban_do_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "ban-do.html", media_type="text/html")


@router.get("/gia-dao")
def gia_dao_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "gia-dao.html", media_type="text/html")


@router.get("/kinh-te")
def kinh_te_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "kinh-te.html", media_type="text/html")


@router.get("/trach-cat")
def trach_cat_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "trach-cat.html", media_type="text/html")


@router.get("/tam-linh")
def tam_linh_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "tam-linh.html", media_type="text/html")


@router.get("/video")
def video_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "video.html", media_type="text/html")


@router.get("/so-sanh")
def so_sanh_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "pages" / "so-sanh.html", media_type="text/html")


@router.get("/share/{token}")
def share_page(token: str = ApiPath(min_length=20, max_length=100)) -> FileResponse:
    del token
    return FileResponse(
        FRONTEND_DIR / "share.html",
        media_type="text/html",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/offline.html")
def offline_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "offline.html", media_type="text/html")


@router.get("/manifest.json")
def pwa_manifest() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "manifest.json", media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "static" / "js" / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@router.get("/favicon.ico")
def favicon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "static" / "icons" / "icon.svg", media_type="image/svg+xml")


@router.get("/icon.svg")
def pwa_icon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "static" / "icons" / "icon.svg", media_type="image/svg+xml")


@router.get("/i18n.js")
def i18n_script() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "static" / "js" / "i18n.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/nav.js")
def nav_script() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "static" / "js" / "nav.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/api/i18n")
def api_i18n_detect(request: Request) -> dict[str, Any]:
    lang = detect_lang(request)
    return {"lang": lang, "translations": TRANSLATIONS[lang]}


@router.get("/api/i18n/{lang}")
def api_i18n(lang: str) -> dict[str, Any]:
    if lang not in LANG_SUPPORTED:
        raise HTTPException(status_code=404, detail="Ngôn ngữ không được hỗ trợ.")
    return {"lang": lang, "translations": TRANSLATIONS[lang]}


@router.get("/health")
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
        "version": "1.0.0",
    }


@router.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
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


@router.post("/api/auth/login")
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


@router.get("/api/auth/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.get("/api/auth/preferences")
def get_preferences(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, bool]:
    return {
        "training_consent": user.training_consent,
        "notifications_enabled": user.notifications_enabled,
        "analysis_notifications_enabled": user.analysis_notifications_enabled,
        "telegram_linked": user.telegram_chat_id is not None,
    }


@router.put("/api/auth/preferences")
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


@router.post("/api/telegram/link-code")
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


@router.get("/api/profiles")
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


@router.get("/api/profiles/active")
def get_active_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Trả profile đang được chọn làm active. Nếu chưa có, trả profile mới nhất."""
    profile = (
        db.query(Profile)
        .filter_by(user_id=user.id, is_active=True)
        .first()
    )
    if profile is None:
        profile = (
            db.query(Profile)
            .filter_by(user_id=user.id)
            .order_by(Profile.created_at.desc(), Profile.id.desc())
            .first()
        )
    if profile is None:
        return {"active": None}
    return {
        "active": {
            "id": profile.id,
            "ho_ten": profile.ho_ten,
            "ngay_sinh": profile.ngay_sinh,
            "profile": json.loads(profile.profile_json),
        }
    }


@router.post("/api/profiles/{profile_id}/set-active")
def set_active_profile(
    profile_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Đặt profile {profile_id} làm active. Các profile khác của user bị tắt active."""
    profile = (
        db.query(Profile)
        .filter_by(id=profile_id, user_id=user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")
    db.query(Profile).filter_by(user_id=user.id).update({"is_active": False})
    profile.is_active = True
    db.commit()
    db.refresh(profile)
    return {
        "id": profile.id,
        "ho_ten": profile.ho_ten,
        "ngay_sinh": profile.ngay_sinh,
        "is_active": True,
    }


@router.post("/api/ban-do/phan-tich")
async def api_ban_do(
    data: MapAnalysisInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    result: dict[str, Any] = {
        "toa_do": tinh_phuong_vi_tu_toa_do(data.lat, data.lon),
        "huong_dat_do_nguoi_dung_cung_cap": data.huong_dat,
        "duong_dan_ban_do": (
            "https://www.openstreetmap.org/?mlat="
            f"{data.lat:.6f}&mlon={data.lon:.6f}#map=16/{data.lat:.6f}/{data.lon:.6f}"
        ),
        "dia_hinh": phan_tich_dia_hinh(None),
        "ghi_chu": (
            "Hướng nhà do người dùng cung cấp, không thể suy ra từ một tọa độ. "
            "Tọa độ không được lưu. Không đánh giá giá trị, mức an toàn hay khả năng đầu tư của bất động sản."
        ),
    }
    if data.truy_van_do_cao:
        if not os.getenv("GOOGLE_MAPS_API_KEY", "").strip():
            raise HTTPException(
                status_code=503,
                detail="Dịch vụ độ cao chưa được cấu hình; tọa độ chưa được gửi tới Google Maps.",
            )
        try:
            elevation = await lay_elevation(data.lat, data.lon)
        except RuntimeError as exc:
            logger.warning("Map elevation request failed: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        result["dia_hinh"] = phan_tich_dia_hinh(elevation)
        result["nguon_do_cao"] = "Google Maps Elevation API"
    return result


@router.post("/api/gia-dao/phan-tich")
def api_gia_dao(
    data: HouseholdInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    members = []
    for member in data.thanh_vien:
        kua = phan_tich_toan_dien(
            member.ngay_sinh.day,
            member.ngay_sinh.month,
            member.ngay_sinh.year,
            gioi_tinh=member.gioi_tinh,
        )["cung_phi"]
        members.append({
            "ten": member.ten,
            "vai_tro": member.vai_tro,
            "ngay_sinh": member.ngay_sinh.isoformat(),
            "cung_phi": kua,
        })
    try:
        return phan_tich_nhom_gia_dinh(members)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/kinh-te/thi-truong")
async def api_thi_truong(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        return await lay_du_lieu_thi_truong()
    except RuntimeError as exc:
        logger.warning("Market data request failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/trach-cat/loai-viec")
def api_trach_cat_loai_viec(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return {
        "loai_viec": {
            key: value["ten"] for key, value in TRACH_CAT_ACTIVITIES.items()
        },
        "ghi_chu": (
            "Không có mục phẫu thuật/chữa bệnh: không dùng lịch dân gian để trì hoãn chăm sóc y tế."
        ),
    }


@router.post("/api/trach-cat/tim-ngay")
def api_trach_cat_tim_ngay(
    data: TrachCatInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        return tim_ngay_dep(
            data.loai_viec, data.tu_ngay, data.so_ngay_tim, data.so_ket_qua
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/tam-linh/thoi-khoa")
def api_tam_linh_thoi_khoa(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return tao_thoi_khoa_tam_linh()


@router.post("/api/tu-vi-tay/chart")
def api_western_chart(
    data: WesternChartInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return lap_natal_chart(data.ngay, data.thang, data.nam)


@router.post("/api/tu-vi-tay/so-sanh")
def api_western_comparison(
    data: WesternChartInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user)
    east_profile = json.loads(profile.profile_json)
    chart = lap_natal_chart(data.ngay, data.thang, data.nam)
    return {
        "so_sanh": so_sanh_dong_tay(east_profile, chart),
        "chart_tay": chart,
    }


@router.post("/api/phong-thuy/phan-tich")
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


@router.post("/api/phong-thuy/llm-tu-van")
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


@router.get("/api/phong-thuy/phi-tinh")
def api_phi_tinh(
    _user: Annotated[User, Depends(get_current_user)],
    ngay: date | None = None,
) -> dict[str, Any]:
    del _user
    return phi_tinh_ngay(ngay or date.today())


@router.get("/api/su-kien/danh-muc")
def api_danh_muc_su_kien(
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return danh_muc_su_kien()


@router.get("/api/su-kien")
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


@router.post("/api/su-kien", status_code=status.HTTP_201_CREATED)
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


@router.delete("/api/su-kien/{event_id}")
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


@router.get("/api/su-kien/tuan")
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


@router.get("/api/su-kien/dai-han")
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


@router.get("/api/vi-mo/timeline")
def api_timeline_vi_mo(
    user: Annotated[User, Depends(get_current_user)],
    bat_dau: date | None = None,
    so_ngay: int = Query(default=90, ge=1, le=366),
) -> dict[str, Any]:
    del user
    return timeline_vi_mo(bat_dau, so_ngay)


@router.post("/api/moi-truong/hien-tai")
async def api_moi_truong_hien_tai(
    data: EnvironmentInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return await _get_environment_for_user(data.lat, data.lon, user, db)


def _local_today() -> date:
    return datetime.now(timezone(timedelta(hours=7), name="ICT")).date()


async def _build_tong_the_data(
    data: CombinedInput, user: User, db: Session
) -> dict[str, Any]:
    try:
        phong_thuy = phan_tich_toan_dien(
            data.ngay, data.thang, data.nam, data.gioi_tinh,
            data.huong_nha, data.huong_bep, data.huong_phong_ngu,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    start = data.ngay_bat_dau or _local_today()
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
    environment = None
    environment_note = None
    if data.lat is not None and data.lon is not None:
        if os.getenv("OPENWEATHER_API_KEY", "").strip():
            environment = await _get_environment_for_user(data.lat, data.lon, user, db)
        else:
            environment_note = (
                "Chưa có OPENWEATHER_API_KEY; dữ liệu thời tiết và AQI được bỏ qua. "
                "Có thể cấu hình khóa này để bật phần môi trường."
            )
    vi_mo = timeline_vi_mo(start, 90)
    tong_hop = buc_tranh_tong_the(profile, phong_thuy, event_summary, environment)
    return {
        "phong_thuy": phong_thuy,
        "su_kien": event_summary,
        "moi_truong": environment,
        "moi_truong_ghi_chu": environment_note,
        "vi_mo": vi_mo,
        "profile": profile,
        "tong_hop": tong_hop,
    }


@router.post("/api/tong-the")
async def api_tong_the(
    data: CombinedInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return await _build_tong_the_data(data, user, db)


@router.post("/api/tong-the/stream")
async def api_tong_the_stream(
    data: CombinedInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    result = await _build_tong_the_data(data, user, db)

    async def event_stream():
        yield _sse_event("metadata", result)
        async for chunk in stream_tong_the_narrative(result):
            if chunk["type"] == "token":
                yield _sse_event("token", {"content": chunk["content"]})
            elif chunk["type"] == "done":
                yield _sse_event("done", {"parsed": chunk["parsed"]})
            elif chunk["type"] == "error":
                yield _sse_event("error", {"message": chunk["message"]})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


def _sse_event(name: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {body}\n\n"


def _prepare_analysis(
    data: BirthInput, user: User, db: Session
) -> tuple[
    Profile, dict[str, Any], dict[str, float], dict[str, float], list[dict[str, Any]]
]:
    db_profile = (
        db.query(Profile)
        .filter_by(
            user_id=user.id,
            ngay_sinh=f"{data.ngay:02d}/{data.thang:02d}/{data.nam}",
        )
        .first()
    )
    previous_profile = (
        json.loads(db_profile.profile_json) if db_profile is not None else {}
    )
    ho_ten: str = data.ho_ten
    if not ho_ten and db_profile is not None:
        saved_name = db_profile.ho_ten
        if isinstance(saved_name, str) and saved_name:
            ho_ten = saved_name
    saved_hour = previous_profile.get("gio_sinh")
    if saved_hour is not None and (
        type(saved_hour) is not int or not 0 <= saved_hour <= 23
    ):
        raise HTTPException(
            status_code=500,
            detail="Giờ sinh đã lưu trong hồ sơ không hợp lệ.",
        )
    gio_sinh: int | None = (
        data.gio_sinh if data.gio_sinh is not None else saved_hour
    )
    profile_data = phan_tich_ngay_sinh(
        data.ngay,
        data.thang,
        data.nam,
        ho_ten=ho_ten,
        gio_sinh=gio_sinh,
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


@router.post("/api/analyze")
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

    result = validate_and_clean_analysis(result)
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


@router.post("/api/analyze/stream")
async def analyze_stream(
    data: BirthInput,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    db_profile, profile_data, adjusted_scores, weights, history_data = (
        _prepare_analysis(data, user, db)
    )
    system, prompt = build_analysis_prompt(profile_data, adjusted_scores, history_data)
    profile_id = db_profile.id
    user_id = user.id
    user_chat_id = user.telegram_chat_id
    user_notif_enabled = user.analysis_notifications_enabled

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
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Ollama stream returned HTTP %s.", exc.response.status_code
            )
            yield encode_event(
                "error", {"message": _ollama_stream_error_message(exc)}
            )
            return
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
            result = validate_and_clean_analysis(
                _parse_llm_json("".join(generated))
            )
            with SessionLocal() as stream_db:
                prediction = Prediction(
                    profile_id=profile_id,
                    scope="general",
                    chi_so_json=json.dumps(adjusted_scores, ensure_ascii=False),
                    du_doan_json=json.dumps(result, ensure_ascii=False),
                )
                stream_db.add(prediction)
                stream_db.commit()
                stream_db.refresh(prediction)
                prediction_id = prediction.id
        except ValueError as exc:
            yield encode_event("error", {"message": str(exc)})
            return
        except SQLAlchemyError:
            yield encode_event(
                "error", {"message": "Không thể lưu kết quả phân tích vào cơ sở dữ liệu."}
            )
            return
        notification_status = "not_enabled"
        if user_notif_enabled and user_chat_id is not None:
            try:
                from core.notifications import telegram

                attachment = json.dumps(
                    {"profile": profile_data, "phan_tich": result},
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
                # Extract thông tin từ profile_data (robust)
                pd = profile_data or {}
                ho_ten = pd.get("ho_ten") or "Không rõ"

                # Thử nhiều dạng field: ngay_sinh string "1983-03-03", hoặc ngay/thang/nam riêng
                ngay_sinh_raw = pd.get("ngay_sinh") or pd.get("date_of_birth") or ""
                ngay = pd.get("ngay")
                thang = pd.get("thang")
                nam = pd.get("nam")

                if ngay_sinh_raw and not (ngay and thang and nam):
                    # Parse "1983-03-03" hoặc "03/03/1983"
                    raw = str(ngay_sinh_raw).replace("/", "-")
                    parts = raw.split("-")
                    if len(parts) == 3:
                        # Thử cả 2 dạng: YYYY-MM-DD và DD-MM-YYYY
                        if len(parts[0]) == 4:
                            nam, thang, ngay = parts[0], parts[1], parts[2]
                        else:
                            ngay, thang, nam = parts[0], parts[1], parts[2]

                dob = f"{ngay}/{thang}/{nam}" if (ngay and thang and nam) else "Không rõ"

                # Giờ sinh: thử nhiều field
                gio = pd.get("gio_sinh") or pd.get("gio") or data.gio_sinh
                gio_str = f" lúc {gio}h" if gio is not None and gio != "" else ""

                # Escape HTML cho an toàn
                def esc(v):
                    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                caption = (
                    f"🔮 <b>Huyền Học AI — Phân tích hoàn tất</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Hồ sơ: <b>{esc(ho_ten)}</b>\n"
                    f"📅 Ngày sinh: {esc(dob)}{esc(gio_str)}\n"
                    f"🆔 Mã phân tích: #{prediction_id}\n"
                    f"\n"
                    f"📎 File JSON đầy đủ đính kèm bên dưới.\n"
                    f"🔗 Mở app: http://localhost:8000/app"
                )

                await telegram.send_document(
                    user_chat_id,
                    f"phan-tich-{prediction_id}.json",
                    attachment,
                    caption,
                )
                notification_status = "sent"
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "Telegram analysis delivery failed for user %s (%s).",
                    user_id,
                    type(exc).__name__,
                )
                notification_status = "failed"
        yield encode_event(
            "done",
            {
                "parsed": result,
                "prediction_id": prediction_id,
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


@router.post("/api/feedback")
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


@router.post("/api/relearn/{ngay_sinh:path}")
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


@router.get("/api/history/{ngay_sinh:path}")
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


@router.get("/api/lich-van-nien/ngay")
def api_day(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    d: date | None = Query(default=None, description="YYYY-MM-DD"),
    ngay_sinh: str | None = Query(default=None),
) -> dict[str, Any]:
    profile = _get_owned_profile(db, user, ngay_sinh)
    birth_profile = json.loads(profile.profile_json)
    return phan_tich_ngay(d or date.today(), birth_profile["menh_nap_am"], birth_profile["con_giap"])


@router.get("/api/lich-van-nien/tuan")
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


@router.get("/api/lich-van-nien/thang")
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


@router.post("/api/lich-van-nien/llm-tuan")
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
        result = _clean_llm_strings(_parse_llm_json(raw))
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


@router.post("/api/tu-vi/lap-so")
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
    prompt = f"""Diễn giải lá số Tử Vi sau như nội dung văn hóa tham khảo, không khẳng định tương lai và không đưa quyết định y tế, pháp lý hoặc tài chính.

QUY TẮC NGHIÊM NGẶT:
- Chỉ luận giải các cung, sao và trạng thái xuất hiện trong dữ liệu JSON bên dưới.
- Không tự thêm, suy đoán hoặc nhắc đến sao, cung, vị trí hay dữ kiện không có trong JSON.
- Nếu một cung có danh sách chính tinh rỗng, chỉ nói cung đó không có chính tinh; không tự mượn sao ở cung khác.
- Viết mọi giá trị văn bản hoàn toàn bằng tiếng Việt, không dùng chữ Hán hoặc tiếng Anh.
- Chỉ nêu tối đa bốn cung nổi bật và chỉ chọn cung có chính tinh trong dữ liệu.
- Gợi ý phải thực tế, cụ thể, tự nguyện; không biến diễn giải truyền thống thành sự thật khoa học.

DỮ LIỆU LÁ SỐ:
{json.dumps(compact_chart, ensure_ascii=False, indent=2)}

Trả về duy nhất một object JSON theo schema:
{{
  "tong_quan": "...",
  "diem_manh": ["..."],
  "diem_can_luu_y": ["..."],
  "cac_cung_noi_bat": [
    {{"cung": "...", "luan_giai": "...", "hanh_dong": "..."}}
  ],
  "loi_khuyen_tong_the": "..."
}}"""
    try:
        raw = await ollama.generate(
            prompt,
            temperature=0.5,
            json_mode=True,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )
        return _clean_llm_strings(_parse_llm_json(raw))
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@router.post("/api/tu-vi/luan-giai")
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


@router.post("/api/tu-vi/export-pdf")
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


@router.post("/api/analyze/export-pdf")
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


@router.post("/api/hop-tuoi")
def api_compatibility(
    data: BirthPairInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    return compatibility(
        data.ngay_sinh_a.day, data.ngay_sinh_a.month, data.ngay_sinh_a.year,
        data.ngay_sinh_b.day, data.ngay_sinh_b.month, data.ngay_sinh_b.year,
    )


@router.post("/api/tarot")
async def api_tarot(
    data: TarotInput,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    del user
    try:
        return await luan_giai_tarot(data.cau_hoi, data.so_la)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@router.post("/api/kinh-dich")
async def api_kinh_dich(data: KinhDichInput) -> dict[str, Any]:
    """Gieo quẻ Kinh Dịch — public, KHÔNG cần login, BẮT BUỘC bát tự."""
    from bat_tu.lap_tu_tru import lap_tu_tru
    try:
        bat_tu = lap_tu_tru(data.ngay_sinh, data.gio_sinh, data.gioi_tinh)
        return await luan_giai_que(data.cau_hoi, bat_tu=bat_tu)
    except (httpx.HTTPError, ValueError) as exc:
        raise _ollama_http_error(exc) from exc


@router.post("/api/bat-tu/lap")
async def api_lap_bat_tu(data: BatTuInput) -> dict[str, Any]:
    """Lập tứ trụ từ ngày giờ sinh."""
    from bat_tu.lap_tu_tru import lap_tu_tru
    try:
        return lap_tu_tru(data.ngay_sinh, data.gio_sinh, data.gioi_tinh)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Không lập được bát tự: {exc}") from exc


@router.post("/api/kinh-dich-stream")
async def api_kinh_dich_stream(data: KinhDichInput) -> StreamingResponse:
    """Stream từng section luận giải Kinh Dịch — public, không cần login."""

    async def event_stream():
        # 0. Lập bát tự trước (BẮT BUỘC)
        try:
            from bat_tu.lap_tu_tru import lap_tu_tru, format_bat_tu_context
            bat_tu = lap_tu_tru(data.ngay_sinh, data.gio_sinh, data.gioi_tinh)
        except Exception as exc:
            yield _sse_event("error", {"message": f"Lỗi lập bát tự: {exc}"})
            return

        # 1. Gieo quẻ
        try:
            cast = gieo_que()
            que_chinh_so = cast["que_chinh"]["so"]
            que_bien_so = (cast.get("que_bien") or {}).get("so") or que_chinh_so
        except Exception as exc:
            yield _sse_event("error", {"message": f"Lỗi gieo quẻ: {exc}"})
            return

        # Lấy nguyên văn Hán + Hán-Việt + Dịch + Giảng từ hocvienlyso
        hanvan_goc = None
        try:
            from knowledge.hocvienlyso_cache import format_for_frontend
            hanvan_goc = format_for_frontend(que_chinh_so)
        except Exception:
            pass

        yield _sse_event("cast", {
            **cast,
            "bat_tu": bat_tu,
            "hanvan": hanvan_goc,  # nguyên văn gốc cho frontend
        })

        # 2. Chuẩn bị 3 prompts
        try:
            # ═══ Dùng hocvienlyso (Hán-Việt + Dịch + Giảng NHL) làm tư liệu chính ═══
            context = ""
            try:
                from knowledge.hocvienlyso_cache import format_for_prompt as nhl_prompt
                context = nhl_prompt(que_chinh_so)
                # Giới hạn 1500 chars (~500 tokens) — đủ cho luận giải
                if len(context) > 1500:
                    context = context[:1500] + "..."
            except Exception:
                pass

            # Fallback RAG cũ nếu hocvienlyso thiếu
            if not context:
                from knowledge.kinh_dich_rag import get_context
                context = get_context(que_chinh_so, que_bien_so)

            que_info = _build_que_info(cast)
            que_info = format_bat_tu_context(bat_tu) + "\n" + que_info

            # ═══ Bổ sung ngũ hành quẻ (BẮT BUỘC — luật cứng) ═══
            try:
                from bat_tu.nap_giap import format_quai_ngu_hanh
                nhat_chu_hanh = bat_tu.get("nhat_chu_hanh", "")
                if nhat_chu_hanh:
                    quai_ctx = format_quai_ngu_hanh(cast["que_chinh"], nhat_chu_hanh)
                    que_info = quai_ctx + "\n\n" + que_info
                    # Quẻ biến nếu có
                    if cast.get("que_bien"):
                        quai_bien_ctx = format_quai_ngu_hanh(cast["que_bien"], nhat_chu_hanh)
                        que_info += "\n\n### QUẺ BIẾN:\n" + quai_bien_ctx
            except Exception as exc:
                print(f"[quai_ngu_hanh] Lỗi: {exc}", flush=True)

            print(f"[DEBUG] que_info gửi cho LLM:\n{que_info}\n", flush=True)
            p1 = await _prompt_1_core(data.cau_hoi, que_info, context)
            p2 = await _prompt_2_tam_hop(data.cau_hoi, que_info, cast=cast, bat_tu=bat_tu)
            p3 = await _prompt_3_action(data.cau_hoi, que_info)
        except Exception as exc:
            yield _sse_event("error", {"message": f"Lỗi chuẩn bị prompt: {exc}"})
            return

        SYSTEM = "Bạn là chuyên gia Kinh Dịch. Chỉ trả về JSON object hợp lệ."

        import asyncio
        from services.ollama_client import (
            ollama as _ollama,
            LLAMA_SERVER_URL_7B as _URL_7B,
            LLAMA_SERVER_URL_3B as _URL_3B,
        )

        async def _run_p1():
            try:
                r = await _ollama.generate(
                    p1, system=SYSTEM, temperature=0.3, json_mode=True,
                    timeout=180.0, num_predict=500, base_url=_URL_7B,
                )
                parsed = _safe_parse(r)
                if not parsed.get("ket_luan"):
                    parsed["ket_luan"] = "TĨNH"
                    parsed["ket_luan_y_nghia"] = parsed.get("ket_luan_y_nghia") or "Quẻ ở trạng thái tĩnh — cần quan sát thêm."
                if not parsed.get("luan_giai_hao_dong"):
                    parsed["luan_giai_hao_dong"] = parsed.get("ly_do") or "Không có hào động."
                return ("core", parsed)
            except Exception as e:
                return ("core", {"error": str(e)})

        async def _run_p2():
            try:
                r = await _ollama.generate(
                    p2, system=SYSTEM, temperature=0.7, json_mode=True,
                    timeout=600.0, num_predict=500, base_url=_URL_3B,
                )
                return ("hao_chuyen", _safe_parse(r))
            except Exception as e:
                return ("hao_chuyen", {"error": str(e)})

        async def _run_p3():
            try:
                r = await _ollama.generate(
                    p3, system=SYSTEM, temperature=0.7, json_mode=True,
                    timeout=600.0, num_predict=600, base_url=_URL_3B,
                )
                return ("que_bien", _safe_parse(r))
            except Exception as e:
                return ("que_bien", {"error": str(e)})        # Chạy p1, p2 song song trên 2 server (7B + 3B)
        _batch1 = [
            asyncio.create_task(_run_p1()),   # 7B
            asyncio.create_task(_run_p2()),   # 3B (đổi URL)
        ]
        for _coro in asyncio.as_completed(_batch1):
            _evt, _payload = await _coro
            yield _sse_event(_evt, _payload)

        # p3 trên 3B
        _evt, _payload = await _run_p3()
        yield _sse_event(_evt, _payload)

        # Lưu diệu nghĩa cá nhân vào DB để unlock sau
        import uuid as _uuid
        _sid = _uuid.uuid4().hex
        try:
            from core.database import cache_personal_insight
            # p3 trả key "dieu_nghia_ca_nhan" (đúng chính tả trong prompt)
            _personal = (
                _payload.get("dieu_nghia_ca_nhan")
                or _payload.get("dien_nghia_ca_nhan")   # fallback nếu LLM gõ nhầm
                or _payload.get("personal_insight")
                or _payload.get("value")
                or ""
            )
            # Nếu là dict → convert thành text
            if isinstance(_personal, dict):
                _parts = []
                for _k, _v in _personal.items():
                    _parts.append(f"**{_k}**\n{_v}")
                _personal = "\n\n".join(_parts)
            elif not isinstance(_personal, str):
                _personal = str(_personal)
            if _personal.strip():
                cache_personal_insight(_sid, _personal)
                print(f"[unlock] ✅ Đã lưu session {_sid} vào DB ({len(_personal)} ký tự)", flush=True)
            else:
                print(f"[unlock] ⚠️ p3 không có dien_nghia_ca_nhan — session {_sid} rỗng", flush=True)
            yield _sse_event("unlock_token", {"session_id": _sid})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"[unlock] ❌ LỖI cache session: {exc}", flush=True)
            yield _sse_event("unlock_token", {"error": str(exc)})

        yield _sse_event("done", {"ok": True})
        return

        import asyncio
        from services.ollama_client import (
            ollama as _ollama,
            LLAMA_SERVER_URL_7B as _URL_7B,
            LLAMA_SERVER_URL_3B as _URL_3B,
        )

        async def _run_p1():
            last_err = None
            for attempt in range(3):
                try:
                    temp = 0.3 + attempt * 0.15
                    r = await _ollama.generate(
                        p1, system=SYSTEM, temperature=temp, json_mode=True,
                        timeout=600.0, num_predict=800, base_url=_URL_7B,
                    )
                    parsed = _safe_parse(r)
                    # Validate: cần ket_luan + luan_giai_hao_dong có data thật
                    has_ket = bool(parsed.get("ket_luan", "").strip())
                    has_hao = bool(parsed.get("luan_giai_hao_dong", "").strip())
                    if has_ket and has_hao:
                        print(f"[p1] OK attempt {attempt+1}: ket_luan={parsed['ket_luan']}", flush=True)
                        return ("core", parsed)
                    print(f"[p1] attempt {attempt+1} fail: ket={has_ket} hao={has_hao}", flush=True)
                except Exception as e:
                    last_err = e
                    print(f"[p1] attempt {attempt+1} error: {e}", flush=True)
            # Fallback cuối cùng
            return ("core", {
                "ket_luan": "TĨNH",
                "ket_luan_y_nghia": "Không đủ dữ liệu để kết luận — cần tham khảo thêm.",
                "luan_giai_hao_dong": "Không có hào động hoặc LLM không trả về dữ liệu.",
                "error": str(last_err) if last_err else "3 lần thử đều thất bại",
            })

        async def _run_p2():
            try:
                r = await _ollama.generate(
                    p2, system=SYSTEM, temperature=0.7, json_mode=True,
                    timeout=600.0, num_predict=500, base_url=_URL_7B,
                )
                return ("hao_chuyen", _safe_parse(r))
            except Exception as e:
                return ("hao_chuyen", {"error": str(e)})

        async def _run_p3():
            try:
                r = await _ollama.generate(
                    p3, system=SYSTEM, temperature=0.7, json_mode=True,
                    timeout=600.0, num_predict=600, base_url=_URL_3B,
                )
                return ("que_bien", _safe_parse(r))
            except Exception as e:
                return ("que_bien", {"error": str(e)})

        _tasks = [
            asyncio.create_task(_run_p1()),
            asyncio.create_task(_run_p2()),
            asyncio.create_task(_run_p3()),
        ]
        for _coro in asyncio.as_completed(_tasks):
            _evt, _payload = await _coro
            yield _sse_event(_evt, _payload)

        try:
            _token = _save_session(cast, bat_tu, data.cau_hoi)
            yield _sse_event("unlock_token", {"token": _token})
        except Exception as exc:
            yield _sse_event("unlock_token", {"error": str(exc)})

        yield _sse_event("done", {"ok": True})
        return

        async def run_one(label: str, prompt: str, temp: float):
            try:
                raw = await ollama.generate(
                    prompt, system=SYSTEM, temperature=temp,
                    json_mode=True, timeout=180.0,
                )
                parsed = _clean_obj(_safe_parse(raw))
                return (label, parsed, None)
            except Exception as exc:
                return (label, None, str(exc))

        # 3. Chạy 3 prompts song song — yield từng kết quả khi xong
        #    Tách riêng phần "dieu_nghia_ca_nhan" của p3 → paywall
        tasks = [
            asyncio.create_task(run_one("core", p1, 0.7)),
            asyncio.create_task(run_one("hao_chuyen", p2, 0.6)),
            asyncio.create_task(run_one("que_bien", p3, 0.7)),
        ]

        # Cache để unlock sau này (per session)
        _pending_personal: dict[str, Any] = {}

        for fut in asyncio.as_completed(tasks):
            label, parsed, err = await fut
            if err:
                yield _sse_event("error", {"message": err, "section": label})
            else:
                # Tách "dieu_nghia_ca_nhan" khỏi p3 (que_bien)
                if label == "que_bien" and parsed:
                    personal = parsed.pop("dieu_nghia_ca_nhan", None)
                    # Fallback: dùng xu_huong + loi_khuyen làm dieu nghia nếu LLM bỏ field
                    if not personal:
                        xu = parsed.get("xu_huong", "")
                        lk = parsed.get("loi_khuyen", "")
                        if xu or lk:
                            personal = (xu + "\n\n" + lk).strip()
                            print(f"[unlock] LLM bỏ dieu_nghia_ca_nhan, dùng fallback ({len(personal)} ký tự)", flush=True)
                    if personal:
                        _pending_personal["value"] = personal
                    else:
                        print("[unlock] CẢNH BÁO: không có dieu_nghia_ca_nhan và không có fallback", flush=True)
                yield _sse_event(label, parsed or {})

        # Gửi token/session để unlock sau
        if _pending_personal.get("value"):
            # Session id đơn giản — dùng hash của câu hỏi + thời gian
            import hashlib, time
            sid = hashlib.md5(
                f"{data.cau_hoi}{time.time()}".encode()
            ).hexdigest()[:16]
            # Lưu vào cache — convert về string an toàn
            try:
                from core.database import cache_personal_insight
                val = _pending_personal["value"]
                # Nếu là dict (LLM trả nested) → convert thành text
                if isinstance(val, dict):
                    parts = []
                    for k, v in val.items():
                        parts.append(f"**{k}**\n{v}")
                    val = "\n\n".join(parts)
                elif not isinstance(val, str):
                    val = str(val)
                cache_personal_insight(sid, val)
                print(f"[unlock] ✅ Đã lưu session {sid} vào DB ({len(val)} ký tự)", flush=True)
            except Exception as exc:
                print(f"[unlock] ❌ LỖI cache session {sid}: {type(exc).__name__}: {exc}", flush=True)
                import traceback
                traceback.print_exc()
            yield _sse_event("unlock_token", {"session_id": sid})

        yield _sse_event("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class UnlockInput(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)


@router.post("/api/kinh-dich/unlock")
async def api_kinh_dich_unlock(data: UnlockInput) -> dict[str, Any]:
    """Mở khoá diệu nghĩa cá nhân (sau khi user xem ads)."""
    from core.database import unlock_personal_insight
    content = unlock_personal_insight(data.session_id)
    if not content:
        raise HTTPException(
            status_code=404,
            detail="Session không tồn tại hoặc đã hết hạn (24h). Vui lòng gieo lại quẻ.",
        )
    return {"ok": True, "dieu_nghia_ca_nhan": content}


@router.post("/api/share")
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


@router.get("/api/share/{token}")
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


@router.delete("/api/share/{token}")
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


@router.post("/api/analyze/ab")
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
        result = validate_and_clean_analysis(_parse_llm_json(raw))
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


@router.get("/api/ab/overview")
def ab_overview(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    return experiment_metrics(db, user.id)


@router.get("/api/admin/ab/overview")
def admin_ab_overview(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    _require_ab_admin(user)
    return experiment_metrics(db)


@router.put("/api/admin/ab/weights")
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


@router.get("/api/dashboard/overview")
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


@router.get("/api/dashboard/raw-feedback")
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
