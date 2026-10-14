"""Lập Tứ Trụ (Bát Tự) từ ngày giờ sinh dương lịch."""
from __future__ import annotations
from datetime import datetime
from typing import Any

import cnlunar


# Can → Ngũ hành
CAN_NGU_HANH = {
    "Giáp": "Mộc", "Ất": "Mộc",
    "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ",
    "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy",
}

# Chi → Ngũ hành
CHI_NGU_HANH = {
    "Tý": "Thủy", "Sửu": "Thổ",
    "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tỵ": "Hỏa",
    "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim",
    "Tuất": "Thổ", "Hợi": "Thủy",
}

# Can Hán → Việt
CAN_HAN_VIET = {
    "甲": "Giáp", "乙": "Ất", "丙": "Bính", "丁": "Đinh", "戊": "Mậu",
    "己": "Kỷ", "庚": "Canh", "辛": "Tân", "壬": "Nhâm", "癸": "Quý",
}

# Chi Hán → Việt
CHI_HAN_VIET = {
    "子": "Tý", "丑": "Sửu", "寅": "Dần", "卯": "Mão", "辰": "Thìn", "巳": "Tỵ",
    "午": "Ngọ", "未": "Mùi", "申": "Thân", "酉": "Dậu", "戌": "Tuất", "亥": "Hợi",
}


def _han_to_viet(gz: str) -> tuple[str, str, str]:
    """Convert Hán tự (VD: 庚午) → (Can Việt, Chi Việt, Full Việt)."""
    if len(gz) != 2:
        return gz, gz, gz
    can = CAN_HAN_VIET.get(gz[0], gz[0])
    chi = CHI_HAN_VIET.get(gz[1], gz[1])
    return can, chi, f"{can} {chi}"


def lap_tu_tru(ngay_sinh: str, gio_sinh: str, gioi_tinh: str = "nam") -> dict[str, Any]:
    """
    Lập tứ trụ từ ngày giờ sinh dương lịch.

    Args:
        ngay_sinh: "YYYY-MM-DD"
        gio_sinh: "HH:MM"
        gioi_tinh: "nam" | "nu"

    Returns:
        Dict chứa tứ trụ (Can Chi Việt), ngũ hành, nhật chủ, âm lịch.
    """
    date = datetime.strptime(f"{ngay_sinh} {gio_sinh}", "%Y-%m-%d %H:%M")
    a = cnlunar.Lunar(date, godType="8char")

    # 4 trụ dạng Hán
    raw = {
        "nam": a.year8Char,
        "thang": a.month8Char,
        "ngay": a.day8Char,
        "gio": a.twohour8Char,
    }

    # Convert sang Việt
    tu_tru = {}
    for tru, gz in raw.items():
        can, chi, full = _han_to_viet(gz)
        tu_tru[tru] = {
            "can": can,
            "chi": chi,
            "full": full,
            "han": gz,
        }

    # Ngũ hành từng trụ
    ngu_hanh = {}
    for tru, v in tu_tru.items():
        ngu_hanh[tru] = {
            "can": CAN_NGU_HANH.get(v["can"], "?"),
            "chi": CHI_NGU_HANH.get(v["chi"], "?"),
        }

    # Đếm ngũ hành (8 chữ)
    hanh_count = {"Kim": 0, "Mộc": 0, "Thủy": 0, "Hỏa": 0, "Thổ": 0}
    for nh in ngu_hanh.values():
        for h in [nh["can"], nh["chi"]]:
            if h in hanh_count:
                hanh_count[h] += 1

    # Nhật chủ = Can ngày
    nhat_chu = tu_tru["ngay"]["can"]
    nhat_chu_hanh = CAN_NGU_HANH.get(nhat_chu, "?")

    # Tìm hành vượng nhất / yếu nhất
    max_hanh = max(hanh_count, key=hanh_count.get)
    min_hanh = min(hanh_count, key=hanh_count.get)

    return {
        "ngay_sinh": ngay_sinh,
        "gio_sinh": gio_sinh,
        "gioi_tinh": gioi_tinh,
        "tu_tru": tu_tru,
        "ngu_hanh": ngu_hanh,
        "hanh_count": hanh_count,
        "nhat_chu": nhat_chu,
        "nhat_chu_hanh": nhat_chu_hanh,
        "hanh_vuong": max_hanh,
        "hanh_yeu": min_hanh,
        "am_duong_lich": {
            "duong": date.strftime("%d/%m/%Y %H:%M"),
            "am": f"{a.lunarYear}/{a.lunarMonth}/{a.lunarDay}",
        },
    }


def format_bat_tu_context(bt: dict[str, Any]) -> str:
    """Format bát tự thành context ngắn cho prompt."""
    tt = bt["tu_tru"]
    hc = bt["hanh_count"]
    return (
        f"### Bát Tự mệnh chủ\n"
        f"- Dương lịch: {bt['am_duong_lich']['duong']}\n"
        f"- Âm lịch: {bt['am_duong_lich']['am']}\n"
        f"- Giới tính: {'Nam' if bt['gioi_tinh'] == 'nam' else 'Nữ'}\n"
        f"- Tứ Trụ: {tt['nam']['full']} / {tt['thang']['full']} / {tt['ngay']['full']} / {tt['gio']['full']}\n"
        f"- Nhật chủ: {bt['nhat_chu']} ({bt['nhat_chu_hanh']})\n"
        f"- Ngũ hành: Kim={hc['Kim']} Mộc={hc['Mộc']} Thủy={hc['Thủy']} Hỏa={hc['Hỏa']} Thổ={hc['Thổ']}\n"
        f"- Hành vượng: {bt['hanh_vuong']}, Hành yếu: {bt['hanh_yeu']}\n"
    )
