# backend/services/action_engine.py
"""
Action Engine — gợi ý hành động dựa trên:
  1. Lịch vạn niên (module có sẵn)
  2. Phong thủy Bát Trạch (module có sẵn)
  3. Giờ hoàng đạo (tính từ Can Chi ngày)
  4. Thời tiết/AQI (OpenWeather)
  5. Hành động cụ thể (rule-based + LLM fallback)
"""
from datetime import date
from typing import Any
import os
import httpx

from services.astrology import phan_tich_ngay_sinh
from divination.lich_van_nien import phan_tich_ngay
from divination.phong_thuy import (
    HUONG_THEO_MUC_DICH,
    hop_huong_nha,
    huong_tot_xau,
    tinh_cung_phi_gioi_tinh,
)


# ─────────────────────────────────────────────
# 1. ACTIONS REGISTRY — Chi tiết theo hành động
# ─────────────────────────────────────────────
ACTIONS = {
    "xuat_hanh": {
        "ten": "Xuất hành / đi xa",
        "mo_ta": "Khởi hành chuyến đi, di chuyển đường dài",
        "uu_tien_gio": ["Mão", "Thìn", "Tỵ", "Ngọ"],
        "uu_tien_huong": ["Đông", "Đông Nam", "Nam"],
        "kieng_gio": ["Dậu", "Tuất"],
        "kieng_huong": ["Tây Bắc"],
        "goi_y": [
            "Khởi hành sớm, tránh giờ Dậu (17-19h)",
            "Kiểm tra thời tiết dọc đường trước khi đi",
            "Mang theo nước uống, điện thoại sạc đầy",
        ],
        "y_nghia": "Xuất hành thuận hướng sẽ hanh thông, ít trở ngại.",
    },
    "ky_ket": {
        "ten": "Ký kết hợp đồng",
        "mo_ta": "Ký hợp đồng, thỏa thuận, cam kết",
        "uu_tien_gio": ["Thìn", "Tỵ", "Ngọ", "Mùi"],
        "uu_tien_huong": ["Đông Nam", "Đông"],
        "kieng_gio": ["Hợi", "Tý"],
        "kieng_huong": ["Tây Bắc"],
        "goi_y": [
            "Đọc kỹ hợp đồng trước khi ký",
            "Chọn giờ hành chính (9-11h) cho rõ ràng",
            "Tránh ký khi tâm trạng bất ổn",
        ],
        "y_nghia": "Ký kết thuận giờ, thuận hướng → hợp tác bền vững.",
    },
    "gap_doi_tac": {
        "ten": "Gặp đối tác",
        "mo_ta": "Gặp gỡ, đàm phán với đối tác",
        "uu_tien_gio": ["Thìn", "Tỵ", "Thân"],
        "uu_tien_huong": ["Tây Bắc", "Tây", "Tây Nam"],
        "kieng_gio": ["Dần", "Mão"],
        "kieng_huong": ["Đông Nam"],
        "goi_y": [
            "Chuẩn bị tài liệu trước 1 ngày",
            "Chọn không gian trung lập (quán cà phê, văn phòng)",
            "Lắng nghe nhiều hơn nói",
        ],
        "y_nghia": "Gặp đối tác đúng hướng → dễ đạt đồng thuận.",
    },
    "khai_truong": {
        "ten": "Khai trương",
        "mo_ta": "Mở cửa hàng, công ty, dự án mới",
        "uu_tien_gio": ["Mão", "Thìn", "Tỵ"],
        "uu_tien_huong": ["Đông Nam", "Nam"],
        "kieng_gio": ["Thân", "Dậu"],
        "kieng_huong": ["Tây Bắc"],
        "goi_y": [
            "Chuẩn bị lễ khai trương đơn giản, không phô trương",
            "Mời người hợp tuổi đến dự",
            "Không khai trương vào ngày Tang môn, Không vong",
        ],
        "y_nghia": "Khai trương đúng ngày giờ → khởi đầu thuận lợi.",
    },
    "mua_sam_lon": {
        "ten": "Mua sắm lớn",
        "mo_ta": "Mua nhà, xe, tài sản lớn",
        "uu_tien_gio": ["Thìn", "Tỵ", "Ngọ"],
        "uu_tien_huong": ["Đông Nam", "Đông"],
        "kieng_gio": ["Hợi", "Tý"],
        "kieng_huong": ["Tây Bắc"],
        "goi_y": [
            "Xem kỹ tài chính trước khi quyết định",
            "Không mua khi đang giận, đang vội",
            "Tham khảo ý kiến người có kinh nghiệm",
        ],
        "y_nghia": "Mua sắm lớn đúng thời điểm → ít rủi ro.",
    },
    "phong_van": {
        "ten": "Phỏng vấn / gặp gỡ",
        "mo_ta": "Phỏng vấn xin việc, gặp gỡ quan trọng",
        "uu_tien_gio": ["Thìn", "Tỵ", "Mùi"],
        "uu_tien_huong": ["Đông", "Đông Bắc"],
        "kieng_gio": ["Dậu", "Tuất"],
        "kieng_huong": ["Tây Nam"],
        "goi_y": [
            "Đến sớm 10-15 phút",
            "Mặc trang phục lịch sự, phù hợp",
            "Chuẩn bị 3 câu hỏi cho người phỏng vấn",
        ],
        "y_nghia": "Gặp gỡ đúng hướng → tự tin, thể hiện tốt.",
    },
    "hoc_tap": {
        "ten": "Học tập",
        "mo_ta": "Học bài, thi cử, nghiên cứu",
        "uu_tien_gio": ["Dần", "Mão", "Thìn"],
        "uu_tien_huong": ["Đông Bắc", "Bắc"],
        "kieng_gio": ["Ngọ", "Mùi"],
        "kieng_huong": ["Nam"],
        "goi_y": [
            "Học vào buổi sáng sớm, đầu óc tỉnh táo",
            "Không học quá 90 phút liên tục",
            "Ngủ đủ 7-8 tiếng trước ngày thi",
        ],
        "y_nghia": "Học đúng giờ, đúng hướng → tập trung cao.",
    },
    "the_thao": {
        "ten": "Thể thao",
        "mo_ta": "Tập luyện, thi đấu thể thao",
        "uu_tien_gio": ["Mão", "Thìn", "Dậu"],
        "uu_tien_huong": ["Nam", "Tây Nam"],
        "kieng_gio": ["Tý", "Sửu"],
        "kieng_huong": ["Bắc"],
        "goi_y": [
            "Khởi động kỹ trước khi tập",
            "Uống đủ nước",
            "Không tập quá sức",
        ],
        "y_nghia": "Tập luyện đúng thời điểm → hiệu quả cao.",
    },
    "nghi_ngoi": {
        "ten": "Nghỉ ngơi",
        "mo_ta": "Nghỉ ngơi, thư giãn, thiền",
        "uu_tien_gio": ["Hợi", "Tý", "Sửu"],
        "uu_tien_huong": ["Tây Bắc", "Bắc"],
        "kieng_gio": ["Ngọ", "Mùi"],
        "kieng_huong": ["Nam"],
        "goi_y": [
            "Tắt điện thoại 1 tiếng trước khi ngủ",
            "Không gian yên tĩnh, ánh sáng dịu",
            "Hít thở sâu 5 phút",
        ],
        "y_nghia": "Nghỉ ngơi đúng cách → phục hồi năng lượng.",
    },
}


# ─────────────────────────────────────────────
# 2. CONVERT giờ Can Chi ↔ giờ số
# ─────────────────────────────────────────────
CAN_CHI_GIO = {
    "Tý": (23, 1), "Sửu": (1, 3), "Dần": (3, 5), "Mão": (5, 7),
    "Thìn": (7, 9), "Tỵ": (9, 11), "Ngọ": (11, 13), "Mùi": (13, 15),
    "Thân": (15, 17), "Dậu": (17, 19), "Tuất": (19, 21), "Hợi": (21, 23),
}

def gio_chi_to_range(gio_chi: str) -> tuple[int, int]:
    return CAN_CHI_GIO.get(gio_chi, (0, 0))

def gio_chi_to_str(gio_chi: str) -> str:
    start, end = CAN_CHI_GIO.get(gio_chi, (0, 0))
    return f"{start}h-{end}h"


# ─────────────────────────────────────────────
# 3. MAIN ADVICE BUILDER
# ─────────────────────────────────────────────
def build_action_advice(
    *,
    action_key: str,
    ngay_sinh: int,
    thang_sinh: int,
    nam_sinh: int,
    gioi_tinh: str,
    target_date: date,
    muc_dich: str = "tai_van",
    huong_nha: str = "Nam",
    thanh_pho: str | None = None,
    quoc_gia: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    thoi_tiet: dict[str, Any] | None = None,
    aqi: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine the selected activity with almanac and personal Kua directions."""
    action = ACTIONS.get(action_key)
    if action is None:
        raise ValueError(f"Hành động không hỗ trợ: {action_key}")
    if muc_dich not in HUONG_THEO_MUC_DICH:
        raise ValueError(f"Mục đích không hỗ trợ: {muc_dich}")

    profile = phan_tich_ngay_sinh(ngay_sinh, thang_sinh, nam_sinh)
    almanac = phan_tich_ngay(target_date, profile["menh_nap_am"], profile["con_giap"])
    kua = tinh_cung_phi_gioi_tinh(ngay_sinh, thang_sinh, nam_sinh, gioi_tinh)
    directions = huong_tot_xau(kua)
    house = hop_huong_nha(kua, huong_nha)

    action_palaces = {
        "xuat_hanh": ("Sinh Khí", "Diên Niên"),
        "ky_ket": ("Sinh Khí", "Thiên Y"),
        "gap_doi_tac": ("Diên Niên", "Sinh Khí"),
        "khai_truong": ("Sinh Khí", "Diên Niên"),
        "mua_sam_lon": ("Sinh Khí", "Thiên Y"),
        "phong_van": ("Thiên Y", "Sinh Khí"),
        "hoc_tap": ("Thiên Y", "Phục Vị"),
        "the_thao": ("Diên Niên", "Sinh Khí"),
        "nghi_ngoi": ("Phục Vị", "Thiên Y"),
    }[action_key]
    purpose_palaces = set(HUONG_THEO_MUC_DICH[muc_dich])
    purpose_directions = [
        item for item in directions["huong_tot"]
        if item["cung"] in purpose_palaces
    ]
    action_directions = [
        item for palace in action_palaces
        for item in purpose_directions if item["cung"] == palace
    ]
    chosen_directions = action_directions or purpose_directions
    direction_names = [item["huong"] for item in chosen_directions]

    good_hours = almanac["gio_hoang_dao"]
    preferred_hours = [hour for hour in action["uu_tien_gio"] if hour in good_hours]
    safe_hours = [hour for hour in preferred_hours if hour not in action["kieng_gio"]]
    if not safe_hours:
        safe_hours = [hour for hour in good_hours if hour not in action["kieng_gio"]]
    if not safe_hours:
        safe_hours = good_hours

    warnings: list[dict[str, str]] = []
    if thoi_tiet:
        temperature = thoi_tiet.get("nhiet_do")
        description = str(thoi_tiet.get("mo_ta", "")).lower()
        if any(word in description for word in ("mưa", "dông", "bão")):
            warnings.append({"muc_do": "cao", "noi_dung": "Thời tiết có mưa hoặc dông; cân nhắc phương án trong nhà."})
        elif isinstance(temperature, (int, float)) and temperature > 35:
            warnings.append({"muc_do": "trung_binh", "noi_dung": "Trời nóng; hạn chế hoạt động ngoài trời vào giữa trưa."})
        elif isinstance(temperature, (int, float)) and temperature < 15:
            warnings.append({"muc_do": "thap", "noi_dung": "Trời lạnh; chuẩn bị trang phục phù hợp."})
    if aqi and aqi.get("index", 0) >= 4:
        warnings.append({"muc_do": "cao", "noi_dung": f"Chất lượng không khí {aqi.get('label', 'kém')}; hạn chế hoạt động gắng sức ngoài trời."})

    best_hour = safe_hours[0] if safe_hours else None
    best_direction = direction_names[0] if direction_names else None
    time_range = gio_chi_to_str(best_hour) if best_hour else "Chưa xác định"
    place = thanh_pho or "địa điểm bạn chọn"
    conclusion = (
        f"Theo lịch tham khảo, ngày này được {almanac['diem_tong_hop']}/100. "
        f"Có thể cân nhắc {action['ten'].lower()} vào {time_range}"
        + (f", ưu tiên hướng {best_direction}" if best_direction else "")
        + f", tại {place}."
    )

    return {
        "hanh_dong": {
            "key": action_key, "ten": action["ten"], "mo_ta": action["mo_ta"],
            "y_nghia": action["y_nghia"], "muc_dich": muc_dich,
        },
        "cung_phi": {"so": kua, "quai": directions["quai"], "nhom": directions["nhom"]},
        "thoi_gian": {
            **almanac,
            "gio_vang": [{"chi": hour, "range": gio_chi_to_str(hour)} for hour in safe_hours],
            "gio_kieng": [{"chi": hour, "range": gio_chi_to_str(hour)} for hour in action["kieng_gio"]],
        },
        "dia_diem": {
            "thanh_pho": thanh_pho, "quoc_gia": quoc_gia, "lat": lat, "lon": lon,
            "huong_nha": house, "huong_cho_hanh_dong": chosen_directions,
            "huong_tot_nhat": best_direction,
        },
        "thoi_tiet": thoi_tiet,
        "aqi": aqi,
        "canh_bao": warnings,
        "goi_y_chi_tiet": action["goi_y"],
        "ket_luan": conclusion,
        "ghi_chu": almanac["ghi_chu"],
    }


async def fetch_weather_openweather(lat: float, lon: float) -> dict | None:
    key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat, "lon": lon, "appid": key,
                    "units": "metric", "lang": "vi",
                },
            )
            r.raise_for_status()
            d = r.json()
            return {
                "nhiet_do": round(d["main"]["temp"], 1),
                "cam_giac": round(d["main"]["feels_like"], 1),
                "do_am": d["main"]["humidity"],
                "mo_ta": d["weather"][0]["description"],
                "gio": d["wind"]["speed"],
                "icon": d["weather"][0]["icon"],
            }
    except Exception:
        return None


async def fetch_aqi_openweather(lat: float, lon: float) -> dict | None:
    key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={"lat": lat, "lon": lon, "appid": key},
            )
            r.raise_for_status()
            d = r.json()
            idx = d["list"][0]["main"]["aqi"]  # 1-5
            labels = {1: "Tốt", 2: "Khá", 3: "Trung bình", 4: "Kém", 5: "Rất kém"}
            return {
                "index": idx,
                "label": labels.get(idx, "Không xác định"),
                "pm2_5": round(d["list"][0]["components"]["pm2_5"], 1),
                "pm10": round(d["list"][0]["components"]["pm10"], 1),
            }
    except Exception:
        return None

async def fetch_aqi(lat: float, lon: float) -> dict | None:
    """Lấy chất lượng không khí từ OpenWeather Air Pollution API."""
    key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={"lat": lat, "lon": lon, "appid": key},
            )
            r.raise_for_status()
            d = r.json()
            idx = d["list"][0]["main"]["aqi"]  # 1-5
            labels = {1: "Tốt", 2: "Khá", 3: "Trung bình", 4: "Kém", 5: "Rất kém"}
            return {
                "index": idx,
                "label": labels.get(idx, "Không xác định"),
                "pm2_5": round(d["list"][0]["components"]["pm2_5"], 1),
                "pm10": round(d["list"][0]["components"]["pm10"], 1),
            }
    except Exception as e:
        print(f"[AQI] ❌ Error: {e}")
        return None

# ─── Alias cho narrative.py ───
fetch_weather = fetch_weather_openweather
