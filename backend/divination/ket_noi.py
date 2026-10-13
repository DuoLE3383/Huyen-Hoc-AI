"""Join planning data without treating cultural scores as causal predictions."""

from datetime import date
from typing import Any


def buc_tranh_tong_the(
    profile: dict[str, Any],
    phong_thuy: dict[str, Any],
    su_kien_tuan: dict[str, Any],
    moi_truong: dict[str, Any] | None = None,
) -> dict[str, Any]:
    events = su_kien_tuan.get("su_kien", [])
    sections = [
        {
            "ten": "Phong thủy",
            "tom_tat": f"Cung phi {phong_thuy['cung_phi']} ({phong_thuy['quai']}); "
            f"hướng nhà {phong_thuy['huong_nha']['huong_nha']} được xếp "
            f"{phong_thuy['huong_nha']['cung']} theo bảng Bát Trạch tham khảo.",
        },
        {
            "ten": "Lịch sự kiện",
            "tom_tat": f"Có {len(events)} sự kiện do người dùng nhập trong khoảng "
            f"{su_kien_tuan['tu_ngay']} đến {su_kien_tuan['den_ngay']}.",
        },
    ]
    if moi_truong:
        sections.append({
            "ten": "Môi trường",
            "tom_tat": (
                f"{moi_truong['thoi_tiet'].get('thanh_pho') or 'Vị trí đã chọn'}: "
                f"{moi_truong['thoi_tiet'].get('mo_ta') or 'đã nhận dữ liệu'}, "
                f"AQI {moi_truong['khong_khi']['aqi']} "
                f"({moi_truong['khong_khi']['muc_do']})."
            ),
        })
    return {
        "ngay_tong_hop": date.today().isoformat(),
        "menh_chu": {
            "menh_nap_am": profile.get("menh_nap_am"),
            "con_giap": profile.get("con_giap"),
        },
        "cac_yeu_to": sections,
        "hanh_dong_goi_y": [
            "Dùng lịch sự kiện để chuẩn bị công việc và kiểm tra các mốc thực tế.",
            "Với thời tiết, chất lượng không khí hoặc sức khỏe, ưu tiên nguồn và hướng dẫn chính thức.",
            "Không dùng kết quả phong thủy hoặc huyền học để quyết định y tế, pháp lý hay tài chính.",
        ],
        "ghi_chu": (
            "Đây là bản tổng hợp thông tin lập kế hoạch, không phải dự báo, "
            "đánh giá rủi ro cá nhân hay quan hệ nhân quả."
        ),
    }
