import unicodedata
from datetime import date
from typing import Any

from divination.lich_van_nien import ngay_can_chi

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


PYTHAGORAS = {
    letter: value
    for value, letters in enumerate(
        ("", "AJS", "BKT", "CLU", "DMV", "ENW", "FOX", "GPY", "HQZ", "IR"),
    )
    for letter in letters
}
VOWELS = frozenset("AEIOUY")
MASTERNUMBERS = frozenset({11, 22, 33})
HOUR_BRANCHES = (
    ("Tý", "23h–01h"), ("Sửu", "01h–03h"), ("Dần", "03h–05h"),
    ("Mão", "05h–07h"), ("Thìn", "07h–09h"), ("Tỵ", "09h–11h"),
    ("Ngọ", "11h–13h"), ("Mùi", "13h–15h"), ("Thân", "15h–17h"),
    ("Dậu", "17h–19h"), ("Tuất", "19h–21h"), ("Hợi", "21h–23h"),
)
HOUR_STEM_STARTS = (0, 2, 4, 6, 8, 0, 2, 4, 6, 8)


def chuan_hoa_ten(ho_ten: str) -> str:
    """Normalize Vietnamese Latin letters for the illustrative Pythagorean mapping."""
    decomposed = unicodedata.normalize("NFD", ho_ten.upper().replace("Đ", "D"))
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn" and character.isascii() and character.isalpha()
    )


def _reduce_name_number(total: int) -> int:
    while total > 9 and total not in MASTERNUMBERS:
        total = sum(int(digit) for digit in str(total))
    return total


def phan_tich_ten(ho_ten: str) -> dict[str, Any]:
    """Calculate name-letter numerology as a cultural/entertainment reference."""
    normalized = chuan_hoa_ten(ho_ten)
    if not normalized:
        return {
            "so_linh_hon": None,
            "so_nhan_cach": None,
            "so_su_menh": None,
            "ghi_chu": "Không tính được vì tên không có chữ cái Latin A–Z.",
        }
    vowels = sum(PYTHAGORAS[letter] for letter in normalized if letter in VOWELS)
    consonants = sum(PYTHAGORAS[letter] for letter in normalized if letter not in VOWELS)
    full_name = vowels + consonants
    return {
        "so_linh_hon": _reduce_name_number(vowels),
        "so_nhan_cach": _reduce_name_number(consonants),
        "so_su_menh": _reduce_name_number(full_name),
        "ghi_chu": (
            "Thần số học tên là hệ quy chiếu văn hóa/giải trí, phụ thuộc cách viết và "
            "không phải phép đo tính cách hay dự đoán khoa học. Ngũ cách cần dữ liệu "
            "nét chữ Hán nên không được suy ra từ cách viết Latin."
        ),
    }


def phan_tich_gio_sinh(day: int, month: int, year: int, hour: int) -> dict[str, Any]:
    """Return a traditional two-hour branch and stem from the entered local clock hour."""
    if not 0 <= hour <= 23:
        raise ValueError("Giờ sinh phải nằm trong khoảng 0–23.")
    can_day, _ = ngay_can_chi(date(year, month, day))
    branch_index = 0 if hour in (23, 0) else ((hour + 1) // 2) % 12
    branch, time_range = HOUR_BRANCHES[branch_index]
    stem_index = (HOUR_STEM_STARTS[CAN.index(can_day)] + branch_index) % len(CAN)
    return {
        "gio_sinh": f"{hour:02d}:00",
        "can_chi_gio": f"{CAN[stem_index]} {branch}",
        "khoang_gio_tham_khao": time_range,
        "ghi_chu": (
            "Dùng giờ địa phương người nhập và quy ước ngày Can Chi giản lược; "
            "không xét múi giờ, địa điểm hoặc quy ước đổi ngày tại giờ Tý."
        ),
    }


def phan_tich_ngay_sinh(
    day: int,
    month: int,
    year: int,
    ho_ten: str = "",
    gio_sinh: int | None = None,
) -> dict[str, Any]:
    can_chi = tinh_can_chi_nam(year)
    can, chi = can_chi.split()
    cung_phi = tinh_cung_phi(day, month, year)
    profile: dict[str, Any] = {
        "ho_ten": ho_ten,
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
    if ho_ten:
        profile["ten_phan_tich"] = phan_tich_ten(ho_ten)
    if gio_sinh is not None:
        profile["gio_sinh"] = gio_sinh
        profile["gio_sinh_phan_tich"] = phan_tich_gio_sinh(
            day, month, year, gio_sinh
        )
    profile["ghi_chu"] = (
        "Nội dung là diễn giải văn hóa tham khảo, không phải dự đoán khoa học."
    )
    return profile


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
