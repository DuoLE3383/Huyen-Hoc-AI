"""Coordinate helpers for user-supplied locations; no inferred land-quality scores."""

import math
import os
from typing import Any

import httpx

from phong_thuy import HUONG

ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"


def tinh_phuong_vi_tu_toa_do(lat: float, lon: float) -> dict[str, float | str]:
    """Return a north-referenced bearing only when a user supplies a second point."""
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Tọa độ nằm ngoài giới hạn hợp lệ.")
    return {"lat": lat, "lon": lon, "huong": "Chưa xác định"}


def phan_tich_dia_hinh(elevation: float | None) -> dict[str, Any]:
    if elevation is not None and not -500 <= elevation <= 9000:
        raise ValueError("Độ cao nằm ngoài giới hạn hợp lệ.")
    return {
        "do_cao_m": elevation,
        "ghi_chu": "Độ cao là dữ liệu địa lý; không suy ra phong thủy, nguy cơ ngập hoặc mức an toàn.",
    }


async def lay_elevation(lat: float, lon: float) -> float:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Dịch vụ độ cao chưa được cấu hình.")
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        try:
            response = await client.get(
                ELEVATION_URL,
                params={"locations": f"{lat},{lon}", "key": api_key},
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("Không lấy được dữ liệu độ cao từ Google Maps.") from exc
    results = body.get("results")
    if body.get("status") != "OK" or not isinstance(results, list) or not results:
        raise RuntimeError("Google Maps không trả về dữ liệu độ cao hợp lệ.")
    value = results[0].get("elevation")
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RuntimeError("Google Maps trả về độ cao không hợp lệ.")
    return float(value)


def phuong_vi_tu_hai_diem(
    origin_lat: float, origin_lon: float, target_lat: float, target_lon: float
) -> dict[str, Any]:
    for lat, lon in ((origin_lat, origin_lon), (target_lat, target_lon)):
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Tọa độ nằm ngoài giới hạn hợp lệ.")
    lat1 = math.radians(origin_lat)
    lat2 = math.radians(target_lat)
    delta_lon = math.radians(target_lon - origin_lon)
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    bearing = math.degrees(math.atan2(y, x)) % 360
    direction = HUONG[int((bearing + 22.5) // 45) % 8]
    return {"goc_bac_theo_chieu_kim_dong_ho": round(bearing, 1), "huong": direction}
