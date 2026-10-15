"""Nạp Giáp — gán Can Chi cho 6 hào của quẻ theo 8 quái.

Nguồn: Kinh Dịch — Nạp Giáp pháp (京房易傳 Kinh Phòng Dịch Truyện).
"""
from __future__ import annotations
from typing import Any


# ═══ Bảng Nạp Giáp ═══
# Mỗi quái nạp 6 can chi (từ hào 1 đến hào 6 của quái đó)
NAP_GIAP = {
    "Càn":  ["Giáp Tý",  "Giáp Dần",  "Giáp Thìn", "Nhâm Ngọ",  "Nhâm Thân", "Nhâm Tuất"],
    "Khôn": ["Ất Mùi",   "Ất Tỵ",     "Ất Mão",    "Quý Sửu",   "Quý Hợi",   "Quý Dậu"],
    "Chấn": ["Canh Tý",  "Canh Dần",  "Canh Thìn", "Canh Ngọ",  "Canh Thân", "Canh Tuất"],
    "Tốn":  ["Tân Sửu",  "Tân Hợi",   "Tân Dậu",   "Tân Mùi",   "Tân Tỵ",    "Tân Mão"],
    "Khảm": ["Mậu Dần",  "Mậu Thìn",  "Mậu Ngọ",   "Mậu Thân",  "Mậu Tuất",  "Mậu Tý"],
    "Ly":   ["Kỷ Mão",   "Kỷ Sửu",    "Kỷ Hợi",    "Kỷ Dậu",    "Kỷ Mùi",    "Kỷ Tỵ"],
    "Cấn":  ["Bính Thìn","Bính Ngọ",  "Bính Thân","Bính Tuất", "Bính Tý",   "Bính Dần"],
    "Đoài": ["Đinh Tỵ",  "Đinh Mão",  "Đinh Sửu",  "Đinh Hợi",  "Đinh Dậu",  "Đinh Mùi"],
}


# ═══ Ngũ hành của Can ═══
CAN_HANH = {
    "Giáp": "Mộc", "Ất": "Mộc",
    "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ",
    "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy",
}

# ═══ Ngũ hành của Chi ═══
CHI_HANH = {
    "Tý": "Thủy", "Sửu": "Thổ", "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tỵ": "Hỏa", "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim", "Tuất": "Thổ", "Hợi": "Thủy",
}

# ═══ Tương sinh: Mộc → Hỏa → Thổ → Kim → Thủy → Mộc ═══
TUONG_SINH = {
    "Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim",
    "Kim": "Thủy", "Thủy": "Mộc",
}

# ═══ Tương khắc: Mộc khắc Thổ, Thổ khắc Thủy, ... ═══
TUONG_KHAC = {
    "Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa",
    "Hỏa": "Kim", "Kim": "Mộc",
}


def _parse_gz(gz: str) -> tuple[str, str]:
    """Tách 'Giáp Tý' → ('Giáp', 'Tý')."""
    parts = gz.split()
    if len(parts) != 2:
        return gz, ""
    return parts[0], parts[1]


def _sinh_khac(a: str, b: str) -> str:
    """Quan hệ ngũ hành giữa a và b.

    Returns:
        'sinh' — a sinh b (a là mẹ, b là con)
        'duoc_sinh' — b sinh a
        'khac' — a khắc b
        'bi_khac' — b khắc a
        'hoa' — a = b (tỷ hòa)
    """
    if a == b:
        return "hoa"
    if TUONG_SINH.get(a) == b:
        return "sinh"
    if TUONG_SINH.get(b) == a:
        return "duoc_sinh"
    if TUONG_KHAC.get(a) == b:
        return "khac"
    if TUONG_KHAC.get(b) == a:
        return "bi_khac"
    return "vo_quan"


def _mo_ta_quan_he(qh: str, hanh_hao: str, hanh_nhat_chu: str) -> str:
    """Mô tả bằng tiếng Việt."""
    if qh == "sinh":
        return f"{hanh_hao} sinh {hanh_nhat_chu} → trợ lực, thuận lợi cho mệnh chủ"
    if qh == "duoc_sinh":
        return f"{hanh_nhat_chu} sinh {hanh_hao} → mệnh chủ bị tiết khí, cần cân nhắc"
    if qh == "khac":
        return f"{hanh_hao} khắc {hanh_nhat_chu} → hào này áp chế mệnh chủ, cần đề phòng"
    if qh == "bi_khac":
        return f"{hanh_nhat_chu} khắc {hanh_hao} → mệnh chủ khắc hào, có thể chế ngự được"
    if qh == "hoa":
        return f"{hanh_hao} tỷ hòa {hanh_nhat_chu} → đồng khí, tương trợ"
    return f"{hanh_hao} và {hanh_nhat_chu} không có quan hệ sinh khắc rõ ràng"


def nap_giap_cho_que(que: dict[str, Any], nhat_chu_hanh: str) -> list[dict[str, Any]]:
    """
    Gán can chi Nạp Giáp cho 6 hào của quẻ.

    Args:
        que: Dict quẻ có 'thuong_quai' + 'ha_quai' + 'hao'
        nhat_chu_hanh: Ngũ hành của nhật chủ mệnh chủ (VD: 'Kim')

    Returns:
        List 6 dict, mỗi dict có:
        {
            vi_tri, can, chi, gz,
            hanh_can, hanh_chi, hanh_chu_dao,
            quan_he_voi_nhat_chu, mo_ta
        }
    """
    thuong_ten = que.get("thuong_quai", {}).get("ten", "")
    ha_ten = que.get("ha_quai", {}).get("ten", "")

    thuong_nap = NAP_GIAP.get(thuong_ten, [])
    ha_nap = NAP_GIAP.get(ha_ten, [])

    ket_qua: list[dict[str, Any]] = []

    for hao in que.get("hao", []):
        vi_tri = hao.get("vi_tri", 0)  # 1..6

        if 1 <= vi_tri <= 3:
            # Hào 1,2,3 → hạ quái (lấy index 0,1,2)
            gz = ha_nap[vi_tri - 1] if len(ha_nap) >= vi_tri else ""
        elif 4 <= vi_tri <= 6:
            # Hào 4,5,6 → thượng quái (lấy index 3,4,5 — KHÔNG phải 0,1,2)
            idx = vi_tri - 1  # 3,4,5
            gz = thuong_nap[idx] if len(thuong_nap) > idx else ""
        else:
            gz = ""

        if not gz:
            continue

        can, chi = _parse_gz(gz)
        hanh_can = CAN_HANH.get(can, "?")
        hanh_chi = CHI_HANH.get(chi, "?")

        # Hành chủ đạo: can chi khác nhau → ưu tiên can (chủ), hoặc chi nếu can là Thổ
        # Theo truyền thống, can chi phối hào; nếu can=chi thì đơn giản
        hanh_chu_dao = hanh_can  # dùng can làm chủ đạo

        qh = _sinh_khac(hanh_chu_dao, nhat_chu_hanh)
        mo_ta = _mo_ta_quan_he(qh, hanh_chu_dao, nhat_chu_hanh)

        ket_qua.append({
            "vi_tri": vi_tri,
            "can": can,
            "chi": chi,
            "gz": gz,
            "hanh_can": hanh_can,
            "hanh_chi": hanh_chi,
            "hanh_chu_dao": hanh_chu_dao,
            "quan_he_voi_nhat_chu": qh,
            "mo_ta": mo_ta,
        })

    return ket_qua


def format_nap_giap_cho_prompt(que: dict[str, Any], nhat_chu_hanh: str) -> str:
    """Format nạp giáp thành context cho LLM prompt."""
    rows = nap_giap_cho_que(que, nhat_chu_hanh)
    if not rows:
        return ""

    lines = [
        "### Nạp Giáp 6 hào (tính sẵn — KHÔNG được bịa thêm)",
        f"Nhật chủ ngũ hành: {nhat_chu_hanh}",
        "",
        "| Hào | Can | Hành Can | Chi | Hành Chi | Quan hệ với Nhật chủ |",
        "|-----|-----|----------|-----|----------|---------------------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['vi_tri']} | {r['can']} | {r['hanh_can']} | {r['chi']} | {r['hanh_chi']} | {r['mo_ta']} |"
        )
    return "\n".join(lines)

# ═══ Ngũ hành của 8 quái ═══
QUAI_NGU_HANH = {
    "Càn": "Kim",   # ☰ Trời
    "Đoài": "Kim",  # ☱ Đầm
    "Ly": "Hỏa",    # ☲ Lửa
    "Chấn": "Mộc",  # ☳ Sấm
    "Tốn": "Mộc",   # ☴ Gió
    "Khảm": "Thủy", # ☵ Nước
    "Cấn": "Thổ",   # ☶ Núi
    "Khôn": "Thổ",  # ☷ Đất
}


def format_quai_ngu_hanh(que: dict[str, Any], nhat_chu_hanh: str) -> str:
    """Format gọn: ngũ hành 2 quái + quan hệ nhật chủ."""
    thuong = que.get("thuong_quai", {}).get("ten", "")
    ha = que.get("ha_quai", {}).get("ten", "")
    hanh_thuong = QUAI_NGU_HANH.get(thuong, "?")
    hanh_ha = QUAI_NGU_HANH.get(ha, "?")

    def _qh(a: str, b: str) -> str:
        if a == b:
            return f"{a} tỷ hòa {b}"
        if TUONG_SINH.get(a) == b:
            return f"{a} sinh {b} → trợ lực"
        if TUONG_SINH.get(b) == a:
            return f"{a} được {b} sinh → có lợi"
        if TUONG_KHAC.get(a) == b:
            return f"{a} khắc {b} → áp chế"
        if TUONG_KHAC.get(b) == a:
            return f"{a} bị {b} khắc → bất lợi"
        return f"{a}/{b}"

    return (
        f"Thượng {thuong}={hanh_thuong}, Hạ {ha}={hanh_ha}, Nhật chủ={nhat_chu_hanh}. "
        f"Thượng: {_qh(hanh_thuong, nhat_chu_hanh)}; Hạ: {_qh(hanh_ha, nhat_chu_hanh)}. "
        f"(Sinh: Mộc→Hỏa→Thổ→Kim→Thủy→Mộc; Khắc: Kim khắc Mộc, Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, Hỏa khắc Kim)"
    )


