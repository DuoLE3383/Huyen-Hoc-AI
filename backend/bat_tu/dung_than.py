"""Tính Dụng Thần, Thập Thần, Cách cục — theo Tử Bình."""
from __future__ import annotations
from typing import Any

from bat_tu.kien_thuc_nen import (
    CAN_NGU_HANH, CHI_NGU_HANH, TANG_CAN,
    TUONG_SINH, TUONG_KHAC, NGU_HOP,
    _thap_than, DUNG_THAN_NHUOC, DUNG_THAN_VUONG,
    HOA_CACH_DUNG_THAN,
)


def tinh_ngu_hanh_count(tu_tru: dict[str, Any]) -> dict[str, float]:
    """Đếm ngũ hành (Can + Chi + Tàng Can) — trả về % tỉ lệ."""
    count = {"Kim": 0.0, "Mộc": 0.0, "Thủy": 0.0, "Hỏa": 0.0, "Thổ": 0.0}
    
    for tru in ["nam", "thang", "ngay", "gio"]:
        t = tu_tru.get(tru, {})
        can = t.get("can", "")
        chi = t.get("chi", "")
        
        # Can
        if can in CAN_NGU_HANH:
            count[CAN_NGU_HANH[can]] += 1.0
        # Chi
        if chi in CHI_NGU_HANH:
            count[CHI_NGU_HANH[chi]] += 1.0
        # Tàng Can
        for tang_can, ti_le in TANG_CAN.get(chi, []):
            if tang_can in CAN_NGU_HANH:
                count[CAN_NGU_HANH[tang_can]] += ti_le
    
    tong = sum(count.values()) or 1.0
    return {h: round(v / tong * 100, 1) for h, v in count.items()}


def nhan_dien_cach_cuc(tu_tru: dict[str, Any], nhat_chu: str) -> dict[str, Any]:
    """Nhận diện Hóa cách (Ất-Canh → Kim, ...)."""
    can_ngay = tu_tru.get("ngay", {}).get("can", "")
    can_gio = tu_tru.get("gio", {}).get("can", "")
    can_thang = tu_tru.get("thang", {}).get("can", "")
    can_nam = tu_tru.get("nam", {}).get("can", "")
    chi_thang = tu_tru.get("thang", {}).get("chi", "")
    
    # Kiểm tra cặp ngũ hợp kề nhau (Ngày-Giờ hoặc Tháng-Ngày)
    for cap, hanh_moi in NGU_HOP.items():
        c1, c2 = cap.split("-")
        # Ngày-Giờ
        if (can_ngay == c1 and can_gio == c2) or (can_ngay == c2 and can_gio == c1):
            return {"loai": "hoa_cach", "cap_hoa": cap, "hanh_moi": hanh_moi, "vi_tri": "ngay-gio"}
        # Tháng-Ngày
        if (can_thang == c1 and can_ngay == c2) or (can_thang == c2 and can_ngay == c1):
            return {"loai": "hoa_cach", "cap_hoa": cap, "hanh_moi": hanh_moi, "vi_tri": "thang-ngay"}
    
    return {"loai": None}


def tinh_dung_than(
    nhat_chu: str,
    ngu_hanh_percent: dict[str, float],
    cach_cuc: dict[str, Any],
) -> dict[str, str]:
    """Tính Dụng Thần, Hỉ thần, Kỵ thần."""
    # 1. Hóa cách
    if cach_cuc.get("loai") == "hoa_cach":
        hanh_moi = cach_cuc.get("hanh_moi")
        info = HOA_CACH_DUNG_THAN.get(hanh_moi, {})
        return {
            "dung_than": info.get("dung", hanh_moi),
            "hy_than": info.get("hy", ""),
            "ky_than": info.get("ky", ""),
            "ly_do": f"Hóa cách {cach_cuc.get('cap_hoa')} → {hanh_moi}",
        }
    
    # 2. Phù Ức
    nhat_chu_hanh = CAN_NGU_HANH.get(nhat_chu, "")
    if not nhat_chu_hanh:
        return {"dung_than": "", "ly_do": "Không xác định được Nhật Chủ"}
    
    # Tính lực Nhật Chủ + Ấn (hành sinh Nhật Chủ)
    an_hanh = None
    for h, s in TUONG_SINH.items():
        if s == nhat_chu_hanh:
            an_hanh = h
            break
    
    luc_nc = ngu_hanh_percent.get(nhat_chu_hanh, 0)
    luc_an = ngu_hanh_percent.get(an_hanh, 0) if an_hanh else 0
    ti_le = luc_nc + luc_an
    
    if ti_le < 55:
        info = DUNG_THAN_NHUOC.get(nhat_chu, {})
        return {
            "dung_than": info.get("dung", ""),
            "hy_than": info.get("hy", ""),
            "ky_than": info.get("ky", ""),
            "ly_do": f"Nhật Chủ Nhược ({ti_le:.1f}% < 55%)",
        }
    else:
        info = DUNG_THAN_VUONG.get(nhat_chu, {})
        return {
            "dung_than": info.get("dung", ""),
            "hy_than": info.get("hy", ""),
            "ky_than": info.get("ky", ""),
            "ly_do": f"Nhật Chủ Vượng ({ti_le:.1f}% ≥ 55%)",
        }


def tinh_thap_than(tu_tru: dict[str, Any], nhat_chu: str) -> dict[str, str]:
    """Tính Thập Thần cho 4 trụ."""
    result = {}
    for tru in ["nam", "thang", "ngay", "gio"]:
        can = tu_tru.get(tru, {}).get("can", "")
        if can:
            result[tru] = _thap_than(nhat_chu, can)
    return result
