"""Telegram bot commands and one-time account linking."""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import (
    Profile,
    SessionLocal,
    TelegramLinkChallenge,
    TelegramPollingState,
    User,
    utcnow_naive,
)
from lich_van_nien import du_doan_tuan, phan_tich_ngay, tong_hop_tuan

logger = logging.getLogger(__name__)
LOCAL_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")


class TelegramBot:
    def __init__(self, token: str | None = None) -> None:
        self.token = token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.base = f"https://api.telegram.org/bot{self.token}" if self.token else None

    async def _request(self, method: str, **kwargs):
        if not self.base:
            raise RuntimeError("TELEGRAM_BOT_TOKEN chưa được cấu hình.")
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.request(method, f"{self.base}/{kwargs.pop('path')}", **kwargs)
            response.raise_for_status()
            payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API từ chối yêu cầu {method}.")
        return payload.get("result")

    async def send_message(self, chat_id: int, text: str) -> None:
        await self._request(
            "POST",
            path="sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )

    async def send_document(
        self, chat_id: int, filename: str, content: bytes, caption: str
    ) -> None:
        await self._request(
            "POST",
            path="sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (filename, content, "application/json")},
        )

    async def get_updates(self, offset: int, timeout: int = 25) -> list[dict]:
        result = await self._request(
            "GET",
            path="getUpdates",
            params={"offset": offset, "timeout": timeout},
            timeout=httpx.Timeout(timeout + 10),
        )
        if not isinstance(result, list):
            raise RuntimeError("Telegram API trả về danh sách update không hợp lệ.")
        return result


telegram = TelegramBot()


def format_daily_message(profile: dict, day_data: dict) -> str:
    score = day_data["diem_tong_hop"]
    signal = "Tốt" if score >= 65 else "Trung bình" if score >= 45 else "Yếu"
    return (
        f"Chào ngày mới!\n\n"
        f"{day_data['thu']}, {day_data['ngay']}\n"
        f"Can Chi: {day_data['can_chi_ngay']} · Tiết khí: {day_data['tiet_khi']}\n"
        f"Quan hệ: {day_data['quan_he_ngu_hanh']} · "
        f"{', '.join(day_data['quan_he_chi'])}\n"
        f"Điểm tham khảo: {score}/100 ({signal})\n"
        f"Giờ hoàng đạo: {', '.join(day_data['gio_hoang_dao'])}\n\n"
        f"Mệnh: {profile['menh_nap_am']} · Con giáp: {profile['con_giap']}\n"
        "Nội dung truyền thống giản lược, chỉ để tham khảo."
    )


def format_weekly_summary(profile: dict, week: dict) -> str:
    best = week["ngay_tot_nhat"]
    worst = week["ngay_xau_nhat"]
    rows = "\n".join(
        f"- {item['thu'][:5]} {item['ngay'][-5:]}: "
        f"{item['diem_tong_hop']}% ({item['can_chi_ngay']})"
        for item in week["danh_sach"]
    )
    return (
        f"Tổng kết tuần tới · Điểm trung bình: {week['diem_trung_binh']}/100\n\n"
        f"Ngày điểm cao nhất: {best['thu']} {best['ngay']} "
        f"({best['diem_tong_hop']}/100)\n"
        f"Ngày điểm thấp nhất: {worst['thu']} {worst['ngay']} "
        f"({worst['diem_tong_hop']}/100)\n\n{rows}\n\n"
        f"Mệnh: {profile['menh_nap_am']} · Con giáp: {profile['con_giap']}\n"
        "Nội dung truyền thống giản lược, chỉ để tham khảo."
    )


def _linked_user(db: Session, chat_id: int) -> User | None:
    return db.query(User).filter(User.telegram_chat_id == chat_id).first()


async def handle_command(chat_id: int, text: str, db: Session) -> None:
    parts = (text or "").strip().split()
    command = parts[0].split("@", 1)[0].lower() if parts else ""

    if command == "/start":
        await telegram.send_message(
            chat_id,
            "Huyền Học AI Bot\n"
            "Dùng /link MA_CODE để liên kết tài khoản từ trang Huyền Học AI.\n"
            "/today — xem lịch hôm nay\n"
            "/week — xem tổng quan tuần\n"
            "/unlink — ngắt liên kết và thông báo",
        )
        return

    if command == "/link":
        if len(parts) != 2 or len(parts[1]) > 100:
            await telegram.send_message(
                chat_id, "Cú pháp: /link MA_CODE (mã lấy từ trang đã đăng nhập)."
            )
            return
        digest = hashlib.sha256(parts[1].encode("utf-8")).hexdigest()
        now = utcnow_naive()
        challenge = (
            db.query(TelegramLinkChallenge)
            .filter(TelegramLinkChallenge.code_digest == digest)
            .first()
        )
        if challenge is None or challenge.expires_at <= now:
            await telegram.send_message(chat_id, "Mã liên kết không hợp lệ hoặc đã hết hạn.")
            return
        user = db.query(User).filter_by(id=challenge.user_id, is_active=True).first()
        if user is None:
            await telegram.send_message(chat_id, "Tài khoản không còn hoạt động.")
            return
        if challenge.used_at is not None:
            if user.telegram_chat_id == chat_id:
                await telegram.send_message(chat_id, "Tài khoản này đã được liên kết.")
                return
            await telegram.send_message(chat_id, "Mã liên kết không hợp lệ hoặc đã hết hạn.")
            return
        other_user = (
            db.query(User)
            .filter(
                User.telegram_chat_id == chat_id,
                User.id != user.id,
            )
            .first()
        )
        if other_user is not None:
            await telegram.send_message(
                chat_id, "Telegram này đã được liên kết với một tài khoản khác."
            )
            return
        user.telegram_chat_id = chat_id
        challenge.used_at = now
        db.commit()
        await telegram.send_message(
            chat_id,
            "Đã liên kết tài khoản. Hãy bật/tắt thông báo hằng ngày trong phần "
            "tùy chọn trên website.",
        )
        return

    user = _linked_user(db, chat_id)
    if command == "/unlink":
        if user is not None:
            user.telegram_chat_id = None
            user.notifications_enabled = False
            user.analysis_notifications_enabled = False
            db.query(TelegramLinkChallenge).filter(
                TelegramLinkChallenge.user_id == user.id,
                TelegramLinkChallenge.used_at.is_(None),
            ).delete(synchronize_session=False)
            db.commit()
        await telegram.send_message(chat_id, "Đã ngắt Telegram; tài khoản web không bị xóa.")
        return

    if command not in {"/today", "/week"}:
        await telegram.send_message(chat_id, "Lệnh không được hỗ trợ. Dùng /start để xem hướng dẫn.")
        return
    if user is None:
        await telegram.send_message(chat_id, "Chưa liên kết. Hãy đăng nhập website và tạo mã bằng nút Telegram.")
        return

    profile_row = db.query(Profile).filter_by(user_id=user.id).order_by(Profile.id.asc()).first()
    if profile_row is None:
        await telegram.send_message(chat_id, "Tài khoản chưa có hồ sơ ngày sinh.")
        return
    profile = json.loads(profile_row.profile_json)
    if command == "/today":
        today = datetime.now(LOCAL_TZ).date()
        day_data = phan_tich_ngay(today, profile["menh_nap_am"], profile["con_giap"])
        await telegram.send_message(chat_id, format_daily_message(profile, day_data))
    else:
        week_data = du_doan_tuan(profile["menh_nap_am"], profile["con_giap"])
        await telegram.send_message(
            chat_id, format_weekly_summary(profile, tong_hop_tuan(week_data))
        )


async def polling_loop() -> None:
    with SessionLocal() as db:
        state = db.get(TelegramPollingState, 1)
        offset = state.next_update_id if state is not None else 0
    logger.info("Telegram polling started.")
    while True:
        try:
            updates = await telegram.get_updates(offset=offset)
            for update in updates:
                update_id = update.get("update_id")
                if not isinstance(update_id, int):
                    continue
                message = update.get("message") or update.get("edited_message")
                db = SessionLocal()
                try:
                    if (
                        isinstance(message, dict)
                        and isinstance(message.get("text"), str)
                        and message.get("chat", {}).get("type") == "private"
                        and isinstance(message.get("chat", {}).get("id"), int)
                    ):
                        await handle_command(
                            message["chat"]["id"], message["text"], db
                        )
                    state = db.get(TelegramPollingState, 1)
                    if state is None:
                        state = TelegramPollingState(id=1, next_update_id=update_id + 1)
                        db.add(state)
                    else:
                        state.next_update_id = update_id + 1
                    db.commit()
                    offset = update_id + 1
                except (httpx.HTTPError, RuntimeError, ValueError, SQLAlchemyError) as exc:
                    db.rollback()
                    logger.warning("Telegram update handling failed (%s).", type(exc).__name__)
                    break
                finally:
                    db.close()
        except asyncio.CancelledError:
            raise
        except (httpx.HTTPError, RuntimeError, ValueError, SQLAlchemyError) as exc:
            logger.error("Telegram polling failed (%s).", type(exc).__name__)
            await asyncio.sleep(5)
