"""Date-only Western sun sign references; no fabricated Moon, rising, or planet positions."""

from datetime import date
from typing import Any

ZODIAC = (
    {"en": "Capricorn", "vn": "Ma Kết", "element": "Đất", "start": (12, 22), "end": (1, 19)},
    {"en": "Aquarius", "vn": "Bảo Bình", "element": "Khí", "start": (1, 20), "end": (2, 18)},
    {"en": "Pisces", "vn": "Song Ngư", "element": "Nước", "start": (2, 19), "end": (3, 20)},
    {"en": "Aries", "vn": "Bạch Dương", "element": "Lửa", "start": (3, 21), "end": (4, 19)},
    {"en": "Taurus", "vn": "Kim Ngưu", "element": "Đất", "start": (4, 20), "end": (5, 20)},
    {"en": "Gemini", "vn": "Song Tử", "element": "Khí", "start": (5, 21), "end": (6, 20)},
    {"en": "Cancer", "vn": "Cự Giải", "element": "Nước", "start": (6, 21), "end": (7, 22)},
    {"en": "Leo", "vn": "Sư Tử", "element": "Lửa", "start": (7, 23), "end": (8, 22)},
    {"en": "Virgo", "vn": "Xử Nữ", "element": "Đất", "start": (8, 23), "end": (9, 22)},
    {"en": "Libra", "vn": "Thiên Bình", "element": "Khí", "start": (9, 23), "end": (10, 22)},
    {"en": "Scorpio", "vn": "Bọ Cạp", "element": "Nước", "start": (10, 23), "end": (11, 21)},
    {"en": "Sagittarius", "vn": "Nhân Mã", "element": "Lửa", "start": (11, 22), "end": (12, 21)},
)


def tinh_sun_sign(day: int, month: int, year: int) -> dict[str, str]:
    date(year, month, day)
    for sign in ZODIAC:
        start_month, start_day = sign["start"]
        end_month, end_day = sign["end"]
        if start_month <= end_month:
            in_range = (
                (month == start_month and day >= start_day)
                or (month == end_month and day <= end_day)
                or start_month < month < end_month
            )
        else:
            in_range = (month == start_month and day >= start_day) or (
                month == end_month and day <= end_day
            )
        if in_range:
            return {"ten": sign["en"], "ten_vi": sign["vn"], "nguyen_to_tham_khao": sign["element"]}
    raise ValueError("Không tính được cung Mặt Trời.")


def lap_natal_chart(day: int, month: int, year: int) -> dict[str, Any]:
    sun = tinh_sun_sign(day, month, year)
    return {
        "ngay_sinh": date(year, month, day).isoformat(),
        "mat_troi": sun,
        "mat_trang": None,
        "cung_moc": None,
        "hanh_tinh_va_goc_chieu": None,
        "ghi_chu": (
            "Chỉ tính cung Mặt Trời theo mốc ngày dương lịch xấp xỉ. "
            "Không tính Mặt Trăng/cung Mọc/hành tinh vì cần thời gian, múi giờ, địa điểm và dữ liệu thiên văn chính xác."
        ),
    }


def so_sanh_dong_tay(eastern_profile: dict[str, Any], western_chart: dict[str, Any]) -> dict[str, Any]:
    return {
        "dong_phuong": {
            "menh_nap_am": eastern_profile.get("menh_nap_am"),
            "con_giap": eastern_profile.get("con_giap"),
        },
        "tay_phuong": western_chart["mat_troi"],
        "doi_chieu": (
            "Đặt hai hệ thống biểu tượng cạnh nhau để tìm câu hỏi tự phản tư; "
            "không quy đổi ngũ hành thành nguyên tố phương Tây hoặc chấm điểm tương hợp."
        ),
    }
