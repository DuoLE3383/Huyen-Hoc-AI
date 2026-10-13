"""Daily and weekly Telegram notifications."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import SQLAlchemyError

from core.database import Profile, SessionLocal, User
from divination.lich_van_nien import du_doan_tuan, phan_tich_ngay, tong_hop_tuan
from core.notifications import (
    format_daily_message,
    format_weekly_summary,
    telegram,
)

logger = logging.getLogger(__name__)
LOCAL_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")
scheduler = AsyncIOScheduler(timezone=LOCAL_TZ)


async def _send_notifications(weekly: bool) -> None:
    db = SessionLocal()
    sent = 0
    try:
        users = (
            db.query(User)
            .filter(
                User.telegram_chat_id.isnot(None),
                User.notifications_enabled.is_(True),
                User.is_active.is_(True),
            )
            .all()
        )
        today = datetime.now(LOCAL_TZ).date()
        for user in users:
            if not isinstance(user.telegram_chat_id, int):
                continue
            profile_row = (
                db.query(Profile)
                .filter_by(user_id=user.id)
                .order_by(Profile.id.asc())
                .first()
            )
            if profile_row is None:
                continue
            try:
                profile = json.loads(profile_row.profile_json)
                if weekly:
                    week = tong_hop_tuan(
                        du_doan_tuan(profile["menh_nap_am"], profile["con_giap"], today)
                    )
                    message = format_weekly_summary(profile, week)
                else:
                    day_data = phan_tich_ngay(
                        today, profile["menh_nap_am"], profile["con_giap"]
                    )
                    message = format_daily_message(profile, day_data)
                await telegram.send_message(user.telegram_chat_id, message)
                sent += 1
                await asyncio.sleep(0.5)
            except (httpx.HTTPError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                logger.warning(
                    "Telegram notification failed for user %s (%s).",
                    user.id,
                    type(exc).__name__,
                )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Unable to load users for Telegram notifications.")
        raise
    finally:
        db.close()
    logger.info("Telegram notification job completed; sent=%s.", sent)


async def send_daily_notifications() -> None:
    await _send_notifications(weekly=False)


async def send_weekly_summary() -> None:
    await _send_notifications(weekly=True)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        send_daily_notifications,
        CronTrigger(hour=7, minute=0, timezone=LOCAL_TZ),
        id="daily_notify",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        send_weekly_summary,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=LOCAL_TZ),
        id="weekly_summary",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
