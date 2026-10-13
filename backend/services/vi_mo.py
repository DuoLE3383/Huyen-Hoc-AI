"""Calendar-scale seasonal markers; not a live news or hazard feed."""

from datetime import date, timedelta
from typing import Any

from divination.lich_van_nien import TIET_KHI
from divination.phong_thuy import phi_tinh_ngay


def timeline_vi_mo(start: date | None = None, days: int = 90) -> dict[str, Any]:
    first_day = start or date.today()
    if not 1 <= days <= 366:
        raise ValueError("days phải nằm trong khoảng 1–366.")
    last_day = first_day + timedelta(days=days - 1)
    year_candidates = {first_day.year, last_day.year}
    events = []
    for year in year_candidates:
        for month, day_number, name in TIET_KHI:
            try:
                marker = date(year, month, day_number)
            except ValueError:
                continue
            if first_day <= marker <= last_day:
                events.append({
                    "ngay": marker.isoformat(),
                    "loai": "tiết khí (mốc lịch xấp xỉ)",
                    "ten": name,
                })
    annual_star = phi_tinh_ngay(first_day)["sao_info"]
    events.sort(key=lambda item: item["ngay"])
    return {
        "tu_ngay": first_day.isoformat(),
        "den_ngay": last_day.isoformat(),
        "su_kien": events,
        "nam": first_day.year,
        "phi_tinh_nam": annual_star,
        "ghi_chu": (
            "Mốc tiết khí là ngày xấp xỉ từ bảng lịch nội bộ. "
            "Không có nguồn tin tức, cảnh báo thiên tai hoặc dự báo xã hội trực tiếp."
        ),
    }
