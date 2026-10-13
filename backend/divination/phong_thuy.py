"""Bát Trạch and simplified annual flying-star reference calculations."""

from datetime import date
from typing import Any

HUONG = ("Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc")

CUNG_PHI_QUAI = {
    1: "Khảm", 2: "Khôn", 3: "Chấn", 4: "Tốn", 5: "Trung",
    6: "Càn", 7: "Đoài", 8: "Cấn", 9: "Ly",
}
DONG_TU_MENH = {1, 3, 4, 9}
CUNG_VI_Y_NGHIA = {
    "Sinh Khí": "Tài lộc và phát triển (diễn giải truyền thống)",
    "Thiên Y": "Sức khỏe và chăm sóc (diễn giải truyền thống)",
    "Diên Niên": "Quan hệ và hòa hợp (diễn giải truyền thống)",
    "Phục Vị": "Ổn định và tĩnh tại (diễn giải truyền thống)",
    "Tuyệt Mệnh": "Một cung bất lợi theo cách diễn giải Bát Trạch",
    "Ngũ Quỷ": "Một cung bất lợi theo cách diễn giải Bát Trạch",
    "Lục Sát": "Một cung bất lợi theo cách diễn giải Bát Trạch",
    "Họa Hại": "Một cung bất lợi theo cách diễn giải Bát Trạch",
}
BAT_TRACH_TABLE = {
    1: {"Sinh Khí": "Đông Nam", "Thiên Y": "Đông", "Diên Niên": "Nam", "Phục Vị": "Bắc",
        "Tuyệt Mệnh": "Tây Nam", "Ngũ Quỷ": "Đông Bắc", "Lục Sát": "Tây Bắc", "Họa Hại": "Tây"},
    2: {"Sinh Khí": "Đông Bắc", "Thiên Y": "Tây", "Diên Niên": "Tây Bắc", "Phục Vị": "Tây Nam",
        "Tuyệt Mệnh": "Bắc", "Ngũ Quỷ": "Đông Nam", "Lục Sát": "Nam", "Họa Hại": "Đông"},
    3: {"Sinh Khí": "Nam", "Thiên Y": "Bắc", "Diên Niên": "Đông Nam", "Phục Vị": "Đông",
        "Tuyệt Mệnh": "Tây", "Ngũ Quỷ": "Tây Bắc", "Lục Sát": "Đông Bắc", "Họa Hại": "Tây Nam"},
    4: {"Sinh Khí": "Bắc", "Thiên Y": "Nam", "Diên Niên": "Đông", "Phục Vị": "Đông Nam",
        "Tuyệt Mệnh": "Đông Bắc", "Ngũ Quỷ": "Tây Nam", "Lục Sát": "Tây", "Họa Hại": "Tây Bắc"},
    5: {"Sinh Khí": "Đông Bắc", "Thiên Y": "Tây", "Diên Niên": "Tây Bắc", "Phục Vị": "Tây Nam",
        "Tuyệt Mệnh": "Bắc", "Ngũ Quỷ": "Đông Nam", "Lục Sát": "Nam", "Họa Hại": "Đông"},
    6: {"Sinh Khí": "Tây", "Thiên Y": "Đông Bắc", "Diên Niên": "Tây Nam", "Phục Vị": "Tây Bắc",
        "Tuyệt Mệnh": "Nam", "Ngũ Quỷ": "Đông", "Lục Sát": "Bắc", "Họa Hại": "Đông Nam"},
    7: {"Sinh Khí": "Tây Bắc", "Thiên Y": "Tây Nam", "Diên Niên": "Đông Bắc", "Phục Vị": "Tây",
        "Tuyệt Mệnh": "Đông", "Ngũ Quỷ": "Nam", "Lục Sát": "Đông Nam", "Họa Hại": "Bắc"},
    8: {"Sinh Khí": "Tây Nam", "Thiên Y": "Tây Bắc", "Diên Niên": "Tây", "Phục Vị": "Đông Bắc",
        "Tuyệt Mệnh": "Đông Nam", "Ngũ Quỷ": "Bắc", "Lục Sát": "Đông", "Họa Hại": "Nam"},
    9: {"Sinh Khí": "Đông", "Thiên Y": "Đông Nam", "Diên Niên": "Bắc", "Phục Vị": "Nam",
        "Tuyệt Mệnh": "Tây Bắc", "Ngũ Quỷ": "Tây", "Lục Sát": "Tây Nam", "Họa Hại": "Đông Bắc"},
}
TOT = ("Sinh Khí", "Thiên Y", "Diên Niên", "Phục Vị")
HUONG_THEO_MUC_DICH = {
    "tai_van": ("Sinh Khí", "Diên Niên"),
    "suc_khoe": ("Thiên Y", "Diên Niên"),
    "tinh_cam": ("Diên Niên", "Phục Vị"),
    "su_nghiep": ("Sinh Khí", "Thiên Y"),
    "hoc_tap": ("Thiên Y", "Phục Vị"),
    "tam_linh": ("Phục Vị", "Sinh Khí"),
}

CUU_TINH = {
    1: {"ten": "Nhất Bạch", "hanh": "Thủy", "cat_hung": "Tham khảo", "y_nghia": "Quan lộc, danh tiếng"},
    2: {"ten": "Nhị Hắc", "hanh": "Thổ", "cat_hung": "Tham khảo", "y_nghia": "Ổn định, chăm sóc"},
    3: {"ten": "Tam Bích", "hanh": "Mộc", "cat_hung": "Tham khảo", "y_nghia": "Giao tiếp, thay đổi"},
    4: {"ten": "Tứ Lục", "hanh": "Mộc", "cat_hung": "Tham khảo", "y_nghia": "Học tập, sáng tạo"},
    5: {"ten": "Ngũ Hoàng", "hanh": "Thổ", "cat_hung": "Tham khảo", "y_nghia": "Trung cung"},
    6: {"ten": "Lục Bạch", "hanh": "Kim", "cat_hung": "Tham khảo", "y_nghia": "Kỷ luật, trách nhiệm"},
    7: {"ten": "Thất Xích", "hanh": "Kim", "cat_hung": "Tham khảo", "y_nghia": "Giao tiếp, trao đổi"},
    8: {"ten": "Bát Bạch", "hanh": "Thổ", "cat_hung": "Tham khảo", "y_nghia": "Tổ chức, tích lũy"},
    9: {"ten": "Cửu Tử", "hanh": "Hỏa", "cat_hung": "Tham khảo", "y_nghia": "Sáng tạo, biểu đạt"},
}
LO_SHU_FLIGHT = (
    "Trung cung", "Tây Bắc", "Tây", "Đông Bắc", "Nam",
    "Bắc", "Tây Nam", "Đông", "Đông Nam",
)


def _digit_sum(value: int) -> int:
    while value > 9:
        value = sum(int(char) for char in str(value))
    return value


def tinh_cung_phi_gioi_tinh(day: int, month: int, year: int, gioi_tinh: str) -> int:
    date(year, month, day)
    if gioi_tinh not in {"nam", "nu"}:
        raise ValueError("gioi_tinh phải là 'nam' hoặc 'nu'.")
    year_digits = _digit_sum(year % 100)
    if year < 2000:
        kua = 10 - year_digits if gioi_tinh == "nam" else year_digits + 5
    else:
        kua = 9 - year_digits if gioi_tinh == "nam" else year_digits + 6
    kua = _digit_sum(kua)
    if kua == 5:
        return 2 if gioi_tinh == "nam" else 8
    return kua


def huong_tot_xau(cung_phi: int) -> dict[str, Any]:
    if cung_phi not in BAT_TRACH_TABLE:
        raise ValueError("Cung phi phải nằm trong khoảng 1–9.")
    table = BAT_TRACH_TABLE[cung_phi]
    return {
        "cung_phi": cung_phi,
        "quai": CUNG_PHI_QUAI[cung_phi],
        "nhom": "Đông tứ mệnh" if cung_phi in DONG_TU_MENH else "Tây tứ mệnh",
        "huong_tot": [
            {"cung": name, "huong": table[name], "y_nghia": CUNG_VI_Y_NGHIA[name], "loai": "tham khảo"}
            for name in TOT
        ],
        "huong_xau": [
            {"cung": name, "huong": table[name], "y_nghia": CUNG_VI_Y_NGHIA[name], "loai": "tham khảo"}
            for name in table if name not in TOT
        ],
    }


def hop_huong_nha(cung_phi: int, huong_nha: str) -> dict[str, Any]:
    if huong_nha not in HUONG:
        raise ValueError("Hướng nhà không hợp lệ.")
    table = BAT_TRACH_TABLE.get(cung_phi)
    if table is None:
        raise ValueError("Cung phi phải nằm trong khoảng 1–9.")
    cung = next(name for name, direction in table.items() if direction == huong_nha)
    return {
        "huong_nha": huong_nha,
        "cung": cung,
        "y_nghia": CUNG_VI_Y_NGHIA[cung],
        "tot": cung in TOT,
        "diem_tham_khao": {"Sinh Khí": 90, "Thiên Y": 80, "Diên Niên": 75, "Phục Vị": 70,
                           "Họa Hại": 30, "Lục Sát": 20, "Ngũ Quỷ": 10, "Tuyệt Mệnh": 5}[cung],
    }


def tinh_nien_phi_tinh(year: int) -> int:
    if year < 1:
        raise ValueError("Năm không hợp lệ.")
    return (11 - _digit_sum(year)) % 9 or 9


def phi_tinh_bay_cung(center_star: int) -> dict[str, dict[str, Any]]:
    if center_star not in CUU_TINH:
        raise ValueError("Sao trung cung phải nằm trong khoảng 1–9.")
    result = {}
    for offset, direction in enumerate(LO_SHU_FLIGHT):
        star = (center_star + offset - 1) % 9 + 1
        result[direction] = {"sao": star, **CUU_TINH[star]}
    return result


def phi_tinh_ngay(day: date) -> dict[str, Any]:
    star = tinh_nien_phi_tinh(day.year)
    return {
        "ngay": day.isoformat(),
        "sao_trung_cung": star,
        "sao_info": CUU_TINH[star],
        "bay_cung": phi_tinh_bay_cung(star),
        "ghi_chu": "Bảng phi tinh năm giản lược; không dùng làm căn cứ cho quyết định quan trọng.",
    }


def phan_tich_toan_dien(
    day: int,
    month: int,
    year: int,
    gioi_tinh: str = "nam",
    huong_nha: str = "Nam",
    huong_bep: str | None = None,
    huong_phong_ngu: str | None = None,
) -> dict[str, Any]:
    kua = tinh_cung_phi_gioi_tinh(day, month, year, gioi_tinh)
    directions = huong_tot_xau(kua)
    result: dict[str, Any] = {
        **directions,
        "huong_nha": hop_huong_nha(kua, huong_nha),
        "phi_tinh_hom_nay": phi_tinh_ngay(date.today()),
        "ghi_chu": (
            "Các phép tính phong thủy là nội dung văn hóa tham khảo, không có giá trị dự đoán khoa học. "
            "Cung phi đang dùng năm dương lịch; quy ước có thể khác nếu xét năm âm lịch."
        ),
    }
    if huong_bep is not None:
        result["huong_bep"] = hop_huong_nha(kua, huong_bep)
    if huong_phong_ngu is not None:
        result["huong_phong_ngu"] = hop_huong_nha(kua, huong_phong_ngu)
    return result
