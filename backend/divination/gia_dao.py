"""Group household members by traditional directions without judging relationships."""

from collections import Counter
from typing import Any

from divination.phong_thuy import DONG_TU_MENH, huong_tot_xau


def phan_tich_nhom_gia_dinh(thanh_vien: list[dict[str, Any]]) -> dict[str, Any]:
    if not 1 <= len(thanh_vien) <= 10:
        raise ValueError("Cần cung cấp từ 1 đến 10 thành viên.")
    east = [item for item in thanh_vien if item["cung_phi"] in DONG_TU_MENH]
    west = [item for item in thanh_vien if item["cung_phi"] not in DONG_TU_MENH]
    counts = Counter(
        direction
        for member in thanh_vien
        for direction in (
            item["huong"] for item in huong_tot_xau(member["cung_phi"])["huong_tot"]
        )
    )
    common = [
        {"huong": direction, "so_nguoi": count}
        for direction, count in sorted(counts.items())
        if count == len(thanh_vien)
    ]
    return {
        "so_thanh_vien": len(thanh_vien),
        "thanh_vien": [
            {
                "ten": item["ten"],
                "vai_tro": item["vai_tro"],
                "cung_phi": item["cung_phi"],
                "quai": huong_tot_xau(item["cung_phi"])["quai"],
                "nhom": "Đông tứ mệnh" if item["cung_phi"] in DONG_TU_MENH else "Tây tứ mệnh",
                "huong_tot_tham_khao": [
                    direction["huong"]
                    for direction in huong_tot_xau(item["cung_phi"])["huong_tot"]
                ],
            }
            for item in thanh_vien
        ],
        "so_nguoi_dong_tu": len(east),
        "so_nguoi_tay_tu": len(west),
        "huong_tot_chung": common,
        "ghi_chu": (
            "Ngày sinh và tên chỉ được xử lý trong yêu cầu, không lưu. "
            "Không suy ra mức độ hòa hợp, xung đột hoặc cách phân phòng từ ngày sinh."
        ),
    }
