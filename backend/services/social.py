"""Privacy-preserving compatibility summaries and revocable share tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Any

from services.astrology import phan_tich_ngay_sinh
from core.database import ShareLink, utcnow_naive


def create_share_link(
    db: Any, user_id: int, payload: dict[str, Any], expires_in_days: int = 30
) -> tuple[str, ShareLink]:
    token = secrets.token_urlsafe(32)
    row = ShareLink(
        user_id=user_id,
        token_digest=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        payload_json=__import__("json").dumps(payload, ensure_ascii=False),
        expires_at=utcnow_naive() + timedelta(days=expires_in_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return token, row


def get_share_link(db: Any, token: str) -> ShareLink | None:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = db.query(ShareLink).filter_by(token_digest=digest).first()
    if (
        row is None
        or row.revoked_at is not None
        or row.expires_at <= utcnow_naive()
    ):
        return None
    return row


def revoke_share_link(db: Any, user_id: int, token: str) -> bool:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = (
        db.query(ShareLink)
        .filter_by(user_id=user_id, token_digest=digest, revoked_at=None)
        .first()
    )
    if row is None:
        return False
    row.revoked_at = utcnow_naive()
    db.commit()
    return True


def compatibility(day_a: int, month_a: int, year_a: int,
                  day_b: int, month_b: int, year_b: int) -> dict[str, Any]:
    first = phan_tich_ngay_sinh(day_a, month_a, year_a)
    second = phan_tich_ngay_sinh(day_b, month_b, year_b)
    elements = [first["menh_nap_am"], second["menh_nap_am"]]
    generated_by = {"Mộc": "Thủy", "Hỏa": "Mộc", "Thổ": "Hỏa", "Kim": "Thổ", "Thủy": "Kim"}
    overcome_by = {"Mộc": "Kim", "Hỏa": "Thủy", "Thổ": "Mộc", "Kim": "Hỏa", "Thủy": "Thổ"}
    if elements[0] == elements[1]:
        element_score, element_summary = 75, "Hai người có cùng nạp âm theo cách tính giản lược."
    elif generated_by[elements[0]] == elements[1] or generated_by[elements[1]] == elements[0]:
        element_score, element_summary = 85, "Ngũ hành nạp âm có quan hệ tương sinh theo bảng tham khảo."
    elif overcome_by[elements[0]] == elements[1] or overcome_by[elements[1]] == elements[0]:
        element_score, element_summary = 45, "Ngũ hành nạp âm có quan hệ tương khắc theo bảng tham khảo."
    else:
        element_score, element_summary = 65, "Ngũ hành nạp âm có quan hệ trung tính theo bảng tham khảo."

    number_distance = abs(first["so_chu_dao"] - second["so_chu_dao"])
    number_score = max(40, 100 - number_distance * 12)
    branch_distance = min(
        abs((first["cung_phi"] - second["cung_phi"]) % 9),
        abs((second["cung_phi"] - first["cung_phi"]) % 9),
    )
    overall = round(element_score * 0.5 + number_score * 0.3 + (100 - branch_distance * 10) * 0.2)
    return {
        "diem_tham_khao": max(0, min(100, overall)),
        "cac_yeu_to": {
            "ngu_hanh": {"diem": element_score, "nhan_xet": element_summary},
            "so_chu_dao": {
                "diem": number_score,
                "nhan_xet": f"Khoảng cách giữa hai số chủ đạo là {number_distance}.",
            },
            "cung_phi": {
                "diem": max(0, 100 - branch_distance * 10),
                "nhan_xet": "Chỉ dùng cung phi giản lược như một góc nhìn truyền thống.",
            },
        },
        "goi_y": [
            "Trao đổi trực tiếp về nhu cầu và kỳ vọng thay vì xem điểm số là kết luận.",
            "Dùng những điểm khác biệt để đặt câu hỏi và tìm cách phối hợp.",
        ],
        "ghi_chu": "Điểm số mang tính văn hóa/giải trí, không đo lường chất lượng quan hệ.",
    }
