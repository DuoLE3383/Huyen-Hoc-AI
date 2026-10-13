import json
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import LocationHistory, User, get_db

router = APIRouter(prefix="/api/geocode", tags=["geocode"])


class GeocodeRequest(BaseModel):
    address: str = Field(min_length=3, max_length=200)


def _location_payload(location: LocationHistory) -> dict:
    return {
        "id": location.id,
        "address": location.address,
        "formattedAddress": location.formatted_address,
        "city": location.city,
        "country": location.country,
        "lat": location.lat,
        "lon": location.lon,
        "weather": (
            json.loads(location.weather_json)
            if location.weather_json is not None
            else None
        ),
        "weatherFetchedAt": (
            location.weather_fetched_at.isoformat()
            if location.weather_fetched_at is not None
            else None
        ),
    }


@router.get("/history")
def location_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    locations = (
        db.query(LocationHistory)
        .filter(LocationHistory.user_id == user.id)
        .order_by(LocationHistory.updated_at.desc(), LocationHistory.id.desc())
        .limit(50)
        .all()
    )
    return {"items": [_location_payload(location) for location in locations]}


@router.delete("/history/{location_id}")
def delete_location_history(
    location_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    location = (
        db.query(LocationHistory)
        .filter_by(id=location_id, user_id=user.id)
        .first()
    )
    if location is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ đã lưu.")
    db.delete(location)
    db.commit()
    return {"deleted": True}


@router.post("/")
async def geocode(
    req: GeocodeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    address = " ".join(req.address.split())
    address_key = address.casefold()
    cached = (
        db.query(LocationHistory)
        .filter_by(user_id=user.id, address_key=address_key)
        .first()
    )
    if cached is not None:
        return {**_location_payload(cached), "cached": True}

    key = os.getenv("GEOAPIFY_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="GEOAPIFY_API_KEY chưa cấu hình.")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.geoapify.com/v1/geocode/search",
                params={
                    "text": address,
                    "lang": "vi",
                    "limit": 1,
                    "apiKey": key,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Không thể kết nối tới dịch vụ tra cứu địa chỉ."
        ) from exc

    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="Geoapify key không hợp lệ.")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="Geoapify đang giới hạn yêu cầu.")
    try:
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="Dịch vụ tra cứu địa chỉ trả về lỗi."
        ) from exc

    features = data.get("features", []) if isinstance(data, dict) else []
    if not features:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ.")
    properties = features[0].get("properties", {})
    lat, lon = properties.get("lat"), properties.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise HTTPException(
            status_code=502, detail="Dịch vụ tra cứu địa chỉ trả về tọa độ không hợp lệ."
        )

    location = LocationHistory(
        user_id=user.id,
        address_key=address_key,
        address=address,
        formatted_address=properties.get("formatted") or address,
        city=properties.get("city") or properties.get("town") or properties.get("village") or properties.get("county"),
        country=properties.get("country"),
        lat=lat,
        lon=lon,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return {**_location_payload(location), "cached": False}
