"""Personal event planning with non-predictive, cultural-reference annotations."""

from datetime import date, timedelta
from typing import Any

LOAI_SU_KIEN: dict[str, dict[str, Any]] = {
    "ca_nhan": {"ten": "Cá nhân", "items": [
        {"id": "sinh_nhat", "ten": "Sinh nhật", "anh_huong": ["tinh_than"], "trong_so": 0.6},
        {"id": "ky_hop_dong", "ten": "Ký hợp đồng", "anh_huong": ["su_nghiep"], "trong_so": 0.9},
        {"id": "phau_thuat", "ten": "Lịch khám/thủ thuật", "anh_huong": ["suc_khoe"], "trong_so": 1.0},
        {"id": "cuoi_hoi", "ten": "Cưới hỏi", "anh_huong": ["tinh_duyen"], "trong_so": 1.0},
        {"id": "chuyen_nha", "ten": "Chuyển nhà", "anh_huong": ["phong_thuy"], "trong_so": 0.8},
        {"id": "khoi_nghiep", "ten": "Khởi nghiệp", "anh_huong": ["su_nghiep"], "trong_so": 0.9},
        {"id": "thi_cu", "ten": "Thi cử", "anh_huong": ["hoc_tap"], "trong_so": 0.8},
        {"id": "dau_tu", "ten": "Hạn rà soát khoản đầu tư", "anh_huong": ["tai_chinh"], "trong_so": 0.9},
        {"id": "chuyen_viec", "ten": "Chuyển việc", "anh_huong": ["su_nghiep"], "trong_so": 0.8},
        {"id": "thang_chuc", "ten": "Thăng chức", "anh_huong": ["su_nghiep"], "trong_so": 0.8},
        {"id": "them_thanh_vien", "ten": "Gia đình có thêm thành viên", "anh_huong": ["gia_dinh"], "trong_so": 0.9},
        {"id": "mat_viec", "ten": "Thay đổi công việc", "anh_huong": ["su_nghiep"], "trong_so": 0.9},
        {"id": "du_an_lon", "ten": "Dự án lớn", "anh_huong": ["su_nghiep"], "trong_so": 0.8},
    ]},
}
EVENTS = {
    item["id"]: {**item, "loai": category}
    for category, definition in LOAI_SU_KIEN.items()
    for item in definition["items"]
}


def danh_muc_su_kien() -> dict[str, dict[str, Any]]:
    return LOAI_SU_KIEN


def quet_su_kien_tuan(
    events: list[dict[str, Any]],
    start: date | None = None,
) -> dict[str, Any]:
    first_day = start or date.today()
    last_day = first_day + timedelta(days=6)
    result = []
    for event in events:
        event_day = event["ngay"] if isinstance(event["ngay"], date) else date.fromisoformat(event["ngay"])
        if not first_day <= event_day <= last_day:
            continue
        event_type = event["loai"]
        metadata = EVENTS.get(event_type)
        if metadata is None:
            raise ValueError(f"Loại sự kiện không được hỗ trợ: {event_type}")
        result.append({
            "id": event.get("id"),
            "ten": metadata["ten"],
            "loai": event_type,
            "ngay": event_day.isoformat(),
            "ghi_chu": event.get("note", ""),
            "muc_do_chu_y": metadata["trong_so"],
            "linh_vuc_lien_quan": metadata["anh_huong"],
            "phan_loai": "sự kiện do người dùng cung cấp",
        })
    result.sort(key=lambda item: (item["ngay"], item["ten"]))
    return {
        "tu_ngay": first_day.isoformat(),
        "den_ngay": last_day.isoformat(),
        "tong_su_kien": len(result),
        "su_kien": result,
        "ghi_chu": "Đây là lịch nhắc việc; mức độ chú ý không phải xác suất hay dự đoán sự kiện.",
    }


def du_bao_dai_han(events: list[dict[str, Any]], year: int) -> dict[str, Any]:
    quarters = []
    for quarter in range(1, 5):
        start_month = (quarter - 1) * 3 + 1
        quarter_events = []
        for event in events:
            event_day = event["ngay"] if isinstance(event["ngay"], date) else date.fromisoformat(event["ngay"])
            if event_day.year == year and start_month <= event_day.month < start_month + 3:
                metadata = EVENTS.get(event["loai"])
                if metadata:
                    quarter_events.append({
                        "ngay": event_day.isoformat(),
                        "ten": metadata["ten"],
                        "ghi_chu": event.get("note", ""),
                    })
        quarters.append({"quy": quarter, "su_kien": quarter_events})
    return {
        "nam": year,
        "quy": quarters,
        "ghi_chu": "Lịch kế hoạch chỉ gồm sự kiện do người dùng nhập, không dự đoán sự kiện tương lai.",
    }
