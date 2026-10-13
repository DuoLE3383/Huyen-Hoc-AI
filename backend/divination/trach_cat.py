"""Traditional almanac calendar browsing; never recommends delaying medical care."""

from datetime import date, timedelta
from typing import Any

from divination.lich_van_nien import CHI, ngay_can_chi

TRUC = ("Kiến", "Trừ", "Mãn", "Bình", "Định", "Chấp", "Phá", "Nguy", "Thành", "Thu", "Khai", "Bế")
ACTIVITIES = {
    "cuoi_hoi": {"ten": "Cưới hỏi", "tot": {"Định", "Thành", "Khai"}, "can_nhac": {"Phá", "Nguy"}},
    "khai_truong": {"ten": "Khai trương", "tot": {"Mãn", "Thành", "Khai"}, "can_nhac": {"Phá", "Bế"}},
    "ky_ket": {"ten": "Ký kết", "tot": {"Bình", "Định", "Thành", "Thu"}, "can_nhac": {"Phá", "Nguy"}},
    "xuat_hanh": {"ten": "Xuất hành", "tot": {"Kiến", "Khai"}, "can_nhac": {"Định", "Phá", "Nguy", "Bế"}},
    "dong_tho": {"ten": "Động thổ", "tot": {"Chấp", "Thành"}, "can_nhac": {"Kiến", "Mãn", "Phá"}},
    "nhap_hoc": {"ten": "Nhập học", "tot": {"Định", "Thành", "Khai"}, "can_nhac": {"Phá", "Bế"}},
    "giao_dich": {"ten": "Giao dịch", "tot": {"Mãn", "Bình", "Thu"}, "can_nhac": {"Phá", "Nguy"}},
    "gap_go": {"ten": "Gặp gỡ", "tot": {"Kiến", "Bình", "Khai"}, "can_nhac": {"Phá", "Nguy"}},
    "chuyen_nha": {"ten": "Chuyển nhà", "tot": {"Thành", "Khai"}, "can_nhac": {"Phá", "Bế"}},
}


def danh_gia_ngay_cho_viec(day: date, activity: str) -> dict[str, Any]:
    if activity not in ACTIVITIES:
        raise ValueError("Loại việc không được hỗ trợ.")
    _, branch = ngay_can_chi(day)
    truc = TRUC[(CHI.index(branch) + 2) % 12]
    info = ACTIVITIES[activity]
    score = 50
    reasons = ["Tra cứu Trực theo chu kỳ ngày giản lược, không xét tháng âm lịch."]
    if truc in info["tot"]:
        score += 15
        reasons.append(f"Trực {truc} được xếp thuận cho {info['ten']} theo bảng tham khảo.")
    elif truc in info["can_nhac"]:
        score -= 15
        reasons.append(f"Trực {truc} được xếp cần cân nhắc cho {info['ten']} theo bảng tham khảo.")
    score = max(0, min(100, score))
    return {
        "ngay": day.isoformat(),
        "cong_viec": activity,
        "ten_cong_viec": info["ten"],
        "can_chi_ngay": f"{ngay_can_chi(day)[0]} {branch}",
        "truc": truc,
        "diem_tham_khao": score,
        "dien_giai": reasons,
    }


def tim_ngay_dep(
    activity: str,
    start: date | None = None,
    days: int = 60,
    result_count: int = 5,
) -> dict[str, Any]:
    if activity not in ACTIVITIES:
        raise ValueError("Loại việc không được hỗ trợ.")
    if not 1 <= days <= 90 or not 1 <= result_count <= 20:
        raise ValueError("Khoảng tìm kiếm phải từ 1–90 ngày; số kết quả từ 1–20.")
    first_day = start or date.today()
    candidates = [
        danh_gia_ngay_cho_viec(first_day + timedelta(days=offset), activity)
        for offset in range(days)
    ]
    candidates.sort(key=lambda item: (-item["diem_tham_khao"], item["ngay"]))
    return {
        "cong_viec": activity,
        "tu_ngay": first_day.isoformat(),
        "so_ngay_tim": days,
        "top_ngay_tham_khao": candidates[:result_count],
        "ghi_chu": (
            "Điểm chỉ mã hóa một số quy tắc lịch dân gian giản lược, không dự báo kết quả. "
            "Không dùng để trì hoãn chăm sóc y tế, nghĩa vụ pháp lý hoặc hạn chót thực tế."
        ),
    }
