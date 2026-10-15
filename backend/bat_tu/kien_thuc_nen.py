"""Kiến thức nền Bát Tự — dùng cho suy diễn Kinh Dịch.

Nguồn: vutruhoc.vn (đã xác thực, nhất quán với Nhật Chủ).
"""
from __future__ import annotations

# ═══ Can → Ngũ hành ═══
CAN_NGU_HANH = {
    "Giáp": "Mộc", "Ất": "Mộc",
    "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ",
    "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy",
}

# ═══ Chi → Ngũ hành ═══
CHI_NGU_HANH = {
    "Tý": "Thủy", "Sửu": "Thổ",
    "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tỵ": "Hỏa",
    "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim",
    "Tuất": "Thổ", "Hợi": "Thủy",
}

# ═══ Tàng Can: Địa Chi → [(Can, tỉ lệ)] ═══
TANG_CAN = {
    "Tý":  [("Quý", 1.0)],
    "Sửu": [("Kỷ", 0.6), ("Quý", 0.3), ("Tân", 0.1)],
    "Dần": [("Giáp", 0.6), ("Bính", 0.3), ("Mậu", 0.1)],
    "Mão": [("Ất", 1.0)],
    "Thìn": [("Mậu", 0.6), ("Ất", 0.3), ("Quý", 0.1)],
    "Tỵ":  [("Bính", 0.6), ("Mậu", 0.3), ("Canh", 0.1)],
    "Ngọ": [("Đinh", 0.7), ("Kỷ", 0.3)],
    "Mùi": [("Kỷ", 0.6), ("Đinh", 0.3), ("Ất", 0.1)],
    "Thân": [("Canh", 0.6), ("Nhâm", 0.3), ("Mậu", 0.1)],
    "Dậu": [("Tân", 1.0)],
    "Tuất": [("Mậu", 0.6), ("Tân", 0.3), ("Đinh", 0.1)],
    "Hợi": [("Nhâm", 0.7), ("Giáp", 0.3)],
}

# ═══ Ngũ hành tương sinh / tương khắc ═══
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

# ═══ Ngũ hợp: cặp Can → hành mới ═══
NGU_HOP = {
    "Giáp-Kỷ": "Thổ", "Ất-Canh": "Kim",
    "Bính-Tân": "Thủy", "Đinh-Nhâm": "Mộc",
    "Mậu-Quý": "Hỏa",
}

# ═══ Thập Thần: (Nhật Chủ, Can khác) → Thập Thần ═══
# Quy tắc: so sánh ngũ hành + âm dương
def _thap_than(nhat_chu: str, can: str) -> str:
    """Xác định Thập Thần của `can` so với `nhat_chu`."""
    if nhat_chu == can:
        return "Tỷ Kiên"
    # Xác định quan hệ ngũ hành
    nc_hanh = CAN_NGU_HANH[nhat_chu]
    c_hanh = CAN_NGU_HANH[can]
    
    # Cùng hành
    if nc_hanh == c_hanh:
        # Cùng hành: Tỷ Kiên (cùng âm dương) hoặc Kiếp Tài (khác)
        # Âm dương: Can index chẵn = Dương, lẻ = Âm
        CAN_ORDER = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
        nc_idx = CAN_ORDER.index(nhat_chu)
        c_idx = CAN_ORDER.index(can)
        return "Tỷ Kiên" if (nc_idx % 2 == c_idx % 2) else "Kiếp Tài"
    
    # Quan hệ sinh/khắc
    if TUONG_SINH.get(c_hanh) == nc_hanh:
        # Can sinh Nhật Chủ → Ấn
        CAN_ORDER = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
        nc_idx = CAN_ORDER.index(nhat_chu)
        c_idx = CAN_ORDER.index(can)
        return "Chính Ấn" if (nc_idx % 2 == c_idx % 2) else "Thiên Ấn"
    if TUONG_SINH.get(nc_hanh) == c_hanh:
        # Nhật Chủ sinh Can → Thực Thần / Thương Quan
        CAN_ORDER = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
        nc_idx = CAN_ORDER.index(nhat_chu)
        c_idx = CAN_ORDER.index(can)
        return "Thực Thần" if (nc_idx % 2 == c_idx % 2) else "Thương Quan"
    if TUONG_KHAC.get(nc_hanh) == c_hanh:
        # Nhật Chủ khắc Can → Tài
        CAN_ORDER = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
        nc_idx = CAN_ORDER.index(nhat_chu)
        c_idx = CAN_ORDER.index(can)
        return "Thiên Tài" if (nc_idx % 2 == c_idx % 2) else "Chính Tài"
    if TUONG_KHAC.get(c_hanh) == nc_hanh:
        # Can khắc Nhật Chủ → Quan / Sát
        CAN_ORDER = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
        nc_idx = CAN_ORDER.index(nhat_chu)
        c_idx = CAN_ORDER.index(can)
        return "Thiên Quan" if (nc_idx % 2 == c_idx % 2) else "Chính Quan"
    return "?"

# ═══ Dụng Thần theo Phù Ức (khi Nhật Chủ Nhược) ═══
DUNG_THAN_NHUOC = {
    "Giáp": {"dung": "Thủy", "hy": "Mộc", "ky": "Kim"},
    "Ất":   {"dung": "Thủy", "hy": "Mộc", "ky": "Kim"},
    "Bính": {"dung": "Mộc", "hy": "Hỏa", "ky": "Thủy"},
    "Đinh": {"dung": "Mộc", "hy": "Hỏa", "ky": "Thủy"},
    "Mậu":  {"dung": "Hỏa", "hy": "Thổ", "ky": "Mộc"},
    "Kỷ":   {"dung": "Hỏa", "hy": "Thổ", "ky": "Mộc"},
    "Canh": {"dung": "Thổ", "hy": "Kim", "ky": "Hỏa"},
    "Tân":  {"dung": "Thổ", "hy": "Kim", "ky": "Hỏa"},
    "Nhâm": {"dung": "Kim", "hy": "Thủy", "ky": "Thổ"},
    "Quý":  {"dung": "Kim", "hy": "Thủy", "ky": "Thổ"},
}

# ═══ Dụng Thần theo Phù Ức (khi Nhật Chủ Vượng) ═══
DUNG_THAN_VUONG = {
    "Giáp": {"dung": "Kim", "hy": "Thổ", "ky": "Thủy"},
    "Ất":   {"dung": "Kim", "hy": "Thổ", "ky": "Thủy"},
    "Bính": {"dung": "Thủy", "hy": "Kim", "ky": "Mộc"},
    "Đinh": {"dung": "Thủy", "hy": "Kim", "ky": "Mộc"},
    "Mậu":  {"dung": "Mộc", "hy": "Thủy", "ky": "Hỏa"},
    "Kỷ":   {"dung": "Mộc", "hy": "Thủy", "ky": "Hỏa"},
    "Canh": {"dung": "Hỏa", "hy": "Mộc", "ky": "Thổ"},
    "Tân":  {"dung": "Hỏa", "hy": "Mộc", "ky": "Thổ"},
    "Nhâm": {"dung": "Thổ", "hy": "Hỏa", "ky": "Kim"},
    "Quý":  {"dung": "Thổ", "hy": "Hỏa", "ky": "Kim"},
}

# ═══ Hóa cách → Dụng Thần mới ═══
HOA_CACH_DUNG_THAN = {
    "Thổ":  {"dung": "Thổ", "hy": "Hỏa", "ky": "Mộc"},
    "Kim":  {"dung": "Kim", "hy": "Thổ", "ky": "Hỏa"},
    "Thủy": {"dung": "Thủy", "hy": "Kim", "ky": "Thổ"},
    "Mộc":  {"dung": "Mộc", "hy": "Thủy", "ky": "Kim"},
    "Hỏa":  {"dung": "Hỏa", "hy": "Mộc", "ky": "Thủy"},
}
