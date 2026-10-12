"""Lịch vạn niên và các chỉ số truyền thống mang tính tham khảo."""

from datetime import date, timedelta
from typing import Any

CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]
CAN_NGU_HANH = {
    "Giáp": "Mộc", "Ất": "Mộc", "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ", "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy",
}
CHI_NGU_HANH = {
    "Tý": "Thủy", "Sửu": "Thổ", "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tỵ": "Hỏa", "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim", "Tuất": "Thổ", "Hợi": "Thủy",
}

# 01/01/2000 is Mậu Ngọ in the sexagenary day cycle.
REFERENCE_DATE = date(2000, 1, 1)
REFERENCE_CAN_INDEX = 4
REFERENCE_CHI_INDEX = 6

GIO_HOANG_DAO = {
    "Tý": ["Tý", "Sửu", "Mão", "Ngọ", "Thân", "Dậu"],
    "Sửu": ["Dần", "Mão", "Tỵ", "Thân", "Tuất", "Hợi"],
    "Dần": ["Tý", "Sửu", "Thìn", "Tỵ", "Mùi", "Tuất"],
    "Mão": ["Dần", "Mão", "Ngọ", "Mùi", "Dậu", "Tý"],
    "Thìn": ["Thìn", "Tỵ", "Thân", "Dậu", "Hợi", "Dần"],
    "Tỵ": ["Ngọ", "Mùi", "Tuất", "Hợi", "Sửu", "Thìn"],
    "Ngọ": ["Tý", "Sửu", "Mão", "Ngọ", "Thân", "Dậu"],
    "Mùi": ["Dần", "Mão", "Tỵ", "Thân", "Tuất", "Hợi"],
    "Thân": ["Tý", "Sửu", "Thìn", "Tỵ", "Mùi", "Tuất"],
    "Dậu": ["Dần", "Mão", "Ngọ", "Mùi", "Dậu", "Tý"],
    "Tuất": ["Thìn", "Tỵ", "Thân", "Dậu", "Hợi", "Dần"],
    "Hợi": ["Ngọ", "Mùi", "Tuất", "Hợi", "Sửu", "Thìn"],
}
TIET_KHI = [
    (1, 5, "Tiểu Hàn"), (1, 20, "Đại Hàn"), (2, 4, "Lập Xuân"),
    (2, 19, "Vũ Thủy"), (3, 6, "Kinh Trập"), (3, 21, "Xuân Phân"),
    (4, 5, "Thanh Minh"), (4, 20, "Cốc Vũ"), (5, 6, "Lập Hạ"),
    (5, 21, "Tiểu Mãn"), (6, 6, "Mang Chủng"), (6, 21, "Hạ Chí"),
    (7, 7, "Tiểu Thử"), (7, 23, "Đại Thử"), (8, 8, "Lập Thu"),
    (8, 23, "Xử Thử"), (9, 8, "Bạch Lộ"), (9, 23, "Thu Phân"),
    (10, 8, "Hàn Lộ"), (10, 23, "Sương Giáng"), (11, 7, "Lập Đông"),
    (11, 22, "Tiểu Tuyết"), (12, 7, "Đại Tuyết"), (12, 22, "Đông Chí"),
]
TUONG_SINH = {"Kim": "Thủy", "Thủy": "Mộc", "Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim"}
TUONG_KHAC = {"Kim": "Mộc", "Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim"}
LUC_XUNG = {frozenset(pair) for pair in [
    ("Tý", "Ngọ"), ("Sửu", "Mùi"), ("Dần", "Thân"),
    ("Mão", "Dậu"), ("Thìn", "Tuất"), ("Tỵ", "Hợi"),
]}
LUC_HOP = {frozenset(pair) for pair in [
    ("Tý", "Sửu"), ("Dần", "Hợi"), ("Mão", "Tuất"),
    ("Thìn", "Dậu"), ("Tỵ", "Thân"), ("Ngọ", "Mùi"),
]}
LUC_HAI = {frozenset(pair) for pair in [
    ("Tý", "Mùi"), ("Sửu", "Ngọ"), ("Dần", "Tỵ"),
    ("Mão", "Thìn"), ("Thân", "Hợi"), ("Dậu", "Tuất"),
]}
HINH_PAIRS = {frozenset(pair) for pair in [
    ("Dần", "Tỵ"), ("Tỵ", "Thân"), ("Thân", "Dần"),
    ("Sửu", "Tuất"), ("Tuất", "Mùi"), ("Mùi", "Sửu"),
    ("Tý", "Mão"),
]}
TU_HINH = {"Thìn", "Ngọ", "Dậu", "Hợi"}


def ngay_can_chi(day: date) -> tuple[str, str]:
    delta = (day - REFERENCE_DATE).days
    return (
        CAN[(REFERENCE_CAN_INDEX + delta) % 10],
        CHI[(REFERENCE_CHI_INDEX + delta) % 12],
    )


def gio_hoang_dao(chi_ngay: str) -> list[str]:
    return GIO_HOANG_DAO.get(chi_ngay, []).copy()


def tiet_khi_cua_ngay(day: date) -> str:
    for month, day_number, name in reversed(TIET_KHI):
        if (day.month, day.day) >= (month, day_number):
            return name
    return TIET_KHI[-1][2]


def quan_he_ngu_hanh(first: str, second: str) -> str:
    if first == second:
        return "tỷ hòa"
    if TUONG_SINH.get(first) == second or TUONG_SINH.get(second) == first:
        return "tương sinh"
    if TUONG_KHAC.get(first) == second or TUONG_KHAC.get(second) == first:
        return "tương khắc"
    return "trung tính"


def quan_he_chi(first: str, second: str) -> list[str]:
    pair = frozenset((first, second))
    result = []
    if pair in LUC_XUNG:
        result.append("xung")
    if pair in LUC_HOP:
        result.append("hợp")
    if pair in LUC_HAI:
        result.append("hại")
    if pair in HINH_PAIRS:
        result.append("hình")
    if first == second and first in TU_HINH:
        result.append("tự hình")
    return result or ["bình hòa"]


def phan_tich_ngay(day: date, menh: str, con_giap: str) -> dict[str, Any]:
    can, chi = ngay_can_chi(day)
    element = CAN_NGU_HANH[can]
    relation = quan_he_ngu_hanh(menh, element)
    animal_relation = quan_he_chi(con_giap, chi)

    score = 50 + {"tương sinh": 25, "tỷ hòa": 15, "trung tính": 0, "tương khắc": -25}[relation]
    if "xung" in animal_relation:
        score -= 15
    if "hợp" in animal_relation:
        score += 15
    if "hại" in animal_relation or "hình" in animal_relation:
        score -= 10
    if "tự hình" in animal_relation:
        score -= 10

    return {
        "ngay": day.isoformat(),
        "thu": ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][day.weekday()],
        "can_chi_ngay": f"{can} {chi}",
        "ngu_hanh_ngay": element,
        "quan_he_ngu_hanh": relation,
        "quan_he_chi": animal_relation,
        "tiet_khi": tiet_khi_cua_ngay(day),
        "gio_hoang_dao": gio_hoang_dao(chi),
        "diem_tong_hop": max(0, min(100, score)),
        "ghi_chu": "Điểm và giờ tốt theo quy tắc truyền thống đơn giản hóa, chỉ để tham khảo.",
    }


def du_doan_tuan(menh: str, con_giap: str, start: date | None = None) -> list[dict[str, Any]]:
    first_day = start or date.today()
    return [phan_tich_ngay(first_day + timedelta(days=index), menh, con_giap) for index in range(7)]


def du_doan_thang(menh: str, con_giap: str, year: int, month: int) -> list[dict[str, Any]]:
    current = date(year, month, 1)
    result = []
    while current.month == month:
        result.append(phan_tich_ngay(current, menh, con_giap))
        current += timedelta(days=1)
    return result


def tong_hop_tuan(week_data: list[dict[str, Any]]) -> dict[str, Any]:
    if not week_data:
        return {}
    best = max(week_data, key=lambda item: item["diem_tong_hop"])
    worst = min(week_data, key=lambda item: item["diem_tong_hop"])
    return {
        "diem_trung_binh": round(sum(item["diem_tong_hop"] for item in week_data) / len(week_data), 1),
        "ngay_tot_nhat": best,
        "ngay_xau_nhat": worst,
        "danh_sach": week_data,
    }


def tong_hop_thang(month_data: list[dict[str, Any]]) -> dict[str, Any]:
    if not month_data:
        return {}
    sorted_days = sorted(month_data, key=lambda item: item["diem_tong_hop"], reverse=True)
    scores = [item["diem_tong_hop"] for item in month_data]
    return {
        "diem_trung_binh": round(sum(scores) / len(scores), 1),
        "diem_cao_nhat": max(scores),
        "diem_thap_nhat": min(scores),
        "top_5_tot": sorted_days[:5],
        "top_5_xau": sorted_days[-5:][::-1],
        "danh_sach": month_data,
    }
