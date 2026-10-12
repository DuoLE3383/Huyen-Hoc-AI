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
BAT_QUAI = {
    1: "Càn (Kim)", 2: "Đoài (Kim)", 3: "Ly (Hỏa)", 4: "Chấn (Mộc)",
    5: "Trung cung", 6: "Khảm (Thủy)", 7: "Cấn (Thổ)", 8: "Khôn (Thổ)",
    9: "Tốn (Mộc)",
}
NAP_AM = [
    "Kim", "Hỏa", "Mộc", "Thổ", "Kim", "Hỏa", "Thủy", "Thổ", "Kim", "Mộc",
    "Thủy", "Thổ", "Hỏa", "Mộc", "Thủy", "Kim", "Hỏa", "Mộc", "Thổ", "Kim",
    "Hỏa", "Thủy", "Thổ", "Kim", "Mộc", "Thủy", "Thổ", "Hỏa", "Mộc", "Thủy",
]


def tinh_can_chi_nam(year: int) -> str:
    """Tính Can Chi theo năm dương lịch; chưa hiệu chỉnh theo Tết âm lịch."""
    return f"{CAN[(year - 4) % 10]} {CHI[(year - 4) % 12]}"


def tinh_so_chu_dao(day: int, month: int, year: int) -> int:
    total = sum(int(digit) for digit in f"{day:02d}{month:02d}{year}")
    while total > 9:
        total = sum(int(digit) for digit in str(total))
    return total


def tinh_cung_phi(day: int, month: int, year: int) -> int:
    total = day + month + year
    while total > 9:
        total = sum(int(digit) for digit in str(total))
    return total or 9


def tinh_menh_ngu_hanh(year: int) -> str:
    cycle_index = (year - 4) % 60
    return NAP_AM[cycle_index // 2]


def tinh_tam_tai(day: int, month: int, year: int) -> dict[str, int]:
    return {
        "thien": (day + month) % 10 or 10,
        "dia": (month + year) % 10 or 10,
        "nhan": (day + year) % 10 or 10,
    }


def phan_tich_ngay_sinh(day: int, month: int, year: int) -> dict[str, Any]:
    can_chi = tinh_can_chi_nam(year)
    can, chi = can_chi.split()
    cung_phi = tinh_cung_phi(day, month, year)
    return {
        "ngay_sinh": f"{day:02d}/{month:02d}/{year}",
        "can_chi_nam": can_chi,
        "ngu_hanh_can": CAN_NGU_HANH[can],
        "ngu_hanh_chi": CHI_NGU_HANH[chi],
        "menh_nap_am": tinh_menh_ngu_hanh(year),
        "so_chu_dao": tinh_so_chu_dao(day, month, year),
        "cung_phi": cung_phi,
        "bat_quai": BAT_QUAI[cung_phi],
        "tam_tai": tinh_tam_tai(day, month, year),
        "con_giap": chi,
    }


def tinh_chi_so_su_kien(profile: dict[str, Any]) -> dict[str, float]:
    """Tạo các chỉ số tham khảo (không phải xác suất dự đoán thực tế)."""
    so_chu_dao = profile["so_chu_dao"]
    cung_phi = profile["cung_phi"]
    menh = profile["menh_nap_am"]
    trong_so = {"Kim": 0.85, "Mộc": 0.75, "Thủy": 0.9, "Hỏa": 0.8, "Thổ": 0.7}
    base = trong_so.get(menh, 0.75)
    return {
        "tai_van": min(100, (so_chu_dao * 8 + cung_phi * 3) * base),
        "tinh_duyen": min(100, (so_chu_dao * 5 + cung_phi * 7) * base),
        "su_nghiep": min(100, (so_chu_dao * 7 + cung_phi * 5) * base),
        "suc_khoe": min(100, (10 - abs(so_chu_dao - 5)) * 10 * base),
        "gap_go": min(100, (so_chu_dao * 6 + cung_phi * 6) * base),
        "thay_doi": min(100, (cung_phi * 9 + so_chu_dao * 2) * base),
    }
