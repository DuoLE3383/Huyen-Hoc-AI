"""Public market observations; deliberately contains no personal investment advice."""

from datetime import datetime, timezone
import asyncio
from typing import Any

import httpx

VNINDEX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVNINDEX"
FX_URL = "https://api.frankfurter.app/latest"


async def _fetch_json(
    client: httpx.AsyncClient, url: str, params: dict[str, str]
) -> dict[str, Any]:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Không lấy được dữ liệu thị trường từ nhà cung cấp.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Nhà cung cấp trả về dữ liệu thị trường không hợp lệ.")
    return result


async def lay_vn_index(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    if client is None:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=3.0),
            headers={"User-Agent": "HuyenHocAI/1.0 contact=local-app"},
        ) as owned_client:
            return await lay_vn_index(owned_client)
    body = await _fetch_json(client, VNINDEX_URL, {"range": "1mo", "interval": "1d"})
    chart = body.get("chart", {})
    results = chart.get("result") if isinstance(chart, dict) else None
    if not results or not isinstance(results[0], dict):
        raise RuntimeError("Nhà cung cấp chưa có dữ liệu VN-Index.")
    result = results[0]
    timestamps = result.get("timestamp", [])
    quotes = result.get("indicators", {}).get("quote", [])
    closes = quotes[0].get("close", []) if quotes else []
    valid = [
        (timestamp, close)
        for timestamp, close in zip(timestamps, closes)
        if isinstance(timestamp, int) and isinstance(close, (int, float))
    ]
    if not valid:
        raise RuntimeError("Nhà cung cấp không có giá đóng cửa VN-Index hợp lệ.")
    timestamp, close = valid[-1]
    return {
        "chi_so": "^VNINDEX",
        "gia_tri": float(close),
        "don_vi": "điểm",
        "thoi_diem": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
        "lich_su_dong_cua": [float(value) for _, value in valid[-30:]],
        "nguon": "Yahoo Finance chart endpoint",
    }


async def lay_ty_gia_usd_vnd(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    if client is None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=3.0)) as owned_client:
            return await lay_ty_gia_usd_vnd(owned_client)
    body = await _fetch_json(client, FX_URL, {"from": "USD", "to": "VND"})
    rates = body.get("rates")
    rate = rates.get("VND") if isinstance(rates, dict) else None
    if not isinstance(rate, (int, float)):
        raise RuntimeError("Nhà cung cấp không có tỷ giá USD/VND hợp lệ.")
    return {
        "cap_nhat": body.get("date"),
        "usd_vnd": float(rate),
        "nguon": "Frankfurter (tỷ giá tham chiếu)",
    }


async def lay_du_lieu_thi_truong() -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=3.0),
        headers={"User-Agent": "HuyenHocAI/1.0 contact=local-app"},
    ) as client:
        try:
            vnindex, exchange_rate = await asyncio.gather(
                lay_vn_index(client), lay_ty_gia_usd_vnd(client)
            )
        except RuntimeError:
            raise
    return {
        "vn_index": vnindex,
        "usd_vnd": exchange_rate,
        "cap_nhat": datetime.now(timezone.utc).isoformat(),
        "ghi_chu": (
            "Dữ liệu nguồn công khai có thể trễ hoặc sai khác với sàn. "
            "Không phải tư vấn đầu tư; không suy luận từ ngày sinh hay ngũ hành."
        ),
    }
