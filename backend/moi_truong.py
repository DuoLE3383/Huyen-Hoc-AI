"""Optional OpenWeather current conditions; coordinates are never persisted."""

import os
from typing import Any

import httpx

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


class WeatherProviderError(RuntimeError):
    """Weather provider configuration, availability, or response error."""


async def _get_json(
    client: httpx.AsyncClient, url: str, params: dict[str, Any]
) -> dict[str, Any]:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherProviderError("Không lấy được dữ liệu môi trường từ nhà cung cấp.") from exc
    if not isinstance(result, dict):
        raise WeatherProviderError("Nhà cung cấp trả về dữ liệu không hợp lệ.")
    return result


async def lay_du_lieu_moi_truong(lat: float, lon: float) -> dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        raise WeatherProviderError("Chưa cấu hình OPENWEATHER_API_KEY trên máy chủ.")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Vĩ độ/kinh độ nằm ngoài giới hạn hợp lệ.")

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        weather = await _get_json(
            client,
            WEATHER_URL,
            {"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "vi"},
        )
        air = await _get_json(
            client,
            AIR_URL,
            {"lat": lat, "lon": lon, "appid": api_key},
        )

    main = weather.get("main")
    conditions = weather.get("weather")
    wind = weather.get("wind", {})
    air_items = air.get("list")
    if (
        not isinstance(main, dict)
        or not isinstance(conditions, list)
        or not conditions
        or not isinstance(wind, dict)
    ):
        raise WeatherProviderError("Nhà cung cấp trả về thời tiết thiếu trường bắt buộc.")
    if not isinstance(air_items, list) or not air_items or not isinstance(air_items[0], dict):
        raise WeatherProviderError("Nhà cung cấp trả về chất lượng không khí không hợp lệ.")
    air_main = air_items[0].get("main", {})
    components = air_items[0].get("components", {})
    if not isinstance(air_main, dict) or not isinstance(components, dict):
        raise WeatherProviderError("Nhà cung cấp trả về chỉ số không khí không hợp lệ.")
    aqi = air_main.get("aqi")
    if not isinstance(aqi, int) or not 1 <= aqi <= 5:
        raise WeatherProviderError("Chỉ số AQI từ nhà cung cấp không hợp lệ.")

    condition = conditions[0] if isinstance(conditions[0], dict) else {}
    return {
        "thoi_tiet": {
            "nhiet_do_c": main.get("temp"),
            "do_am_phan_tram": main.get("humidity"),
            "mo_ta": condition.get("description", ""),
            "gio_m_s": wind.get("speed"),
            "thanh_pho": weather.get("name", ""),
        },
        "khong_khi": {
            "aqi": aqi,
            "muc_do": ("Tốt", "Khá", "Trung bình", "Kém", "Rất kém")[aqi - 1],
            "pm2_5": components.get("pm2_5"),
            "pm10": components.get("pm10"),
        },
        "nguon": "OpenWeather",
        "ghi_chu": "Tọa độ chỉ dùng để truy vấn, không được lưu trong hồ sơ.",
    }


def danh_gia_anh_huong_moi_truong(data: dict[str, Any]) -> dict[str, Any]:
    weather = data["thoi_tiet"]
    air = data["khong_khi"]
    actions = []
    aqi = air["aqi"]
    if aqi >= 4:
        actions.append("Cân nhắc giảm hoạt động ngoài trời và theo dõi khuyến cáo chất lượng không khí tại địa phương.")
    elif aqi == 3:
        actions.append("Người nhạy cảm có thể theo dõi chất lượng không khí trước khi hoạt động ngoài trời.")
    if isinstance(weather.get("nhiet_do_c"), (int, float)) and weather["nhiet_do_c"] >= 35:
        actions.append("Tránh nắng nóng kéo dài; uống nước và theo dõi cảnh báo thời tiết chính thức.")
    if isinstance(weather.get("nhiet_do_c"), (int, float)) and weather["nhiet_do_c"] <= 5:
        actions.append("Mặc đủ ấm và theo dõi cảnh báo rét tại địa phương.")
    return {
        "khuyen_nghi_thuc_te": actions,
        "ghi_chu": "Khuyến nghị môi trường dựa trên dữ liệu hiện tại, không phải tư vấn y tế.",
    }
