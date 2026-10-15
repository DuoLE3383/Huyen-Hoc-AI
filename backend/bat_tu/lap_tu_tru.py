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

    # ═══ Tích hợp dung_than (local) ═══
    try:
        from bat_tu.dung_than import (
            tinh_ngu_hanh_count, nhan_dien_cach_cuc,
            tinh_dung_than, tinh_thap_than,
        )
        ngu_hanh_percent = tinh_ngu_hanh_count(tu_tru)
        cach_cuc = nhan_dien_cach_cuc(tu_tru, nhat_chu)
        dung_than = tinh_dung_than(nhat_chu, ngu_hanh_percent, cach_cuc)
        thap_than = tinh_thap_than(tu_tru, nhat_chu)
    except Exception as e:
        ngu_hanh_percent = {}
        cach_cuc = {"loai": None, "error": str(e)}
        dung_than = {}
        thap_than = {}

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
        # ═══ MỚI ═══
        "ngu_hanh_percent": ngu_hanh_percent,
        "cach_cuc": cach_cuc,
        "dung_than": dung_than,
        "thap_than": thap_than,
    }


def format_bat_tu_context(bt: dict[str, Any]) -> str:
    """Format bát tự gọn — chỉ nhật chủ + dụng thần + hào động cần thiết."""
    tt = bt["tu_tru"]
    dt = bt.get("dung_than", {})
    lines = [
        f"Bát Tự: {tt['nam']['full']} / {tt['thang']['full']} / {tt['ngay']['full']} / {tt['gio']['full']}",
        f"Nhật chủ: {bt['nhat_chu']} ({bt['nhat_chu_hanh']})",
    ]
    if dt.get("dung_than"):
        lines.append(f"Dụng Thần: {dt['dung_than']} | Hỉ: {dt.get('hy_than','?')} | Kỵ: {dt.get('ky_than','?')}")
    return "\n".join(lines)


