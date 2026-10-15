"""Crawl Bát Tự từ vutruhoc.vn — nguồn duy nhất (đã xác thực)."""
from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

VUTRUHOC_URL = "https://vutruhoc.vn/bat-tu"


class CrawlError(Exception):
    """Lỗi crawl — dùng để trigger fallback cache."""


async def crawl_vutruhoc(
    ngay: int,
    thang: int,
    nam: int,
    gio: int,
    phut: int,
    gioi_tinh: str,
) -> dict[str, Any]:
    """Crawl Bát Tự từ vutruhoc.vn."""
    gender = "male" if gioi_tinh.lower() == "nam" else "female"
    params = {
        "day": ngay,
        "month": thang,
        "year": nam,
        "hour": gio,
        "minute": phut,
        "gender": gender,
    }

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                VUTRUHOC_URL,
                params=params,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; HuyenHocAI/1.0)",
                    "Accept-Language": "vi,en;q=0.9",
                },
            )
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        raise CrawlError(f"HTTP error: {e}") from e

    soup = BeautifulSoup(html, "html.parser")

    try:
        tu_tru = _parse_tu_tru(soup)
        ngu_hanh = _parse_ngu_hanh(soup)
        dung_than = _parse_dung_than(soup)
        thap_than = _parse_thap_than(soup)
        cach_cuc = _parse_cach_cuc(soup)
    except Exception as e:
        raise CrawlError(f"Parse error: {e}") from e

    return {
        "tu_tru": tu_tru,
        "ngu_hanh": ngu_hanh,
        "dung_than": dung_than,
        "thap_than": thap_than,
        "cach_cuc": cach_cuc,
        "nguon": "vutruhoc.vn",
    }


def _parse_tu_tru(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse bảng Tứ Trụ."""
    result: dict[str, Any] = {}
    tables = soup.find_all("table")
    for table in tables:
        text = table.get_text()
        if "Thiên Can" in text and "Địa Chi" in text:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                label = cells[0].get_text(strip=True)
                values = [c.get_text(strip=True) for c in cells[1:]]
                result[label] = values
            break
    if not result:
        result = _parse_tu_tru_by_text(soup)
    return _normalize_tu_tru(result)


def _parse_tu_tru_by_text(soup: BeautifulSoup) -> dict[str, Any]:
    """Fallback parser — tìm theo text."""
    text = soup.get_text()
    result: dict[str, Any] = {}

    m = re.search(r"Thiên Can\s*\n((?:\s*\S+\s*\n){4})", text)
    if m:
        result["Thiên Can"] = [x.strip() for x in m.group(1).strip().split("\n") if x.strip()]

    m = re.search(r"Địa Chi\s*\n((?:\s*\S+\s*\n){4})", text)
    if m:
        result["Địa Chi"] = [x.strip() for x in m.group(1).strip().split("\n") if x.strip()]

    return result


def _normalize_tu_tru(raw: dict[str, Any]) -> dict[str, Any]:
    """Chuẩn hóa Tứ Trụ về dạng {nam, thang, ngay, gio}."""
    can = raw.get("Thiên Can", [])
    chi = raw.get("Địa Chi", [])
    tang_can = raw.get("Tàng Can", [])
    thap_than = raw.get("Thập Thần", [])
    nap_am = raw.get("Nạp Âm", [])

    def _get(lst, i, default=""):
        return lst[i] if i < len(lst) else default

    return {
        "gio":   {"can": _get(can, 0), "chi": _get(chi, 0), "tang_can": _get(tang_can, 0), "thap_than": _get(thap_than, 0), "nap_am": _get(nap_am, 0)},
        "ngay":  {"can": _get(can, 1), "chi": _get(chi, 1), "tang_can": _get(tang_can, 1), "thap_than": _get(thap_than, 1), "nap_am": _get(nap_am, 1)},
        "thang": {"can": _get(can, 2), "chi": _get(chi, 2), "tang_can": _get(tang_can, 2), "thap_than": _get(thap_than, 2), "nap_am": _get(nap_am, 2)},
        "nam":   {"can": _get(can, 3), "chi": _get(chi, 3), "tang_can": _get(tang_can, 3), "thap_than": _get(thap_than, 3), "nap_am": _get(nap_am, 3)},
        "nhat_chu": _get(can, 1),
    }


def _parse_ngu_hanh(soup: BeautifulSoup) -> dict[str, float]:
    """Parse tỉ lệ ngũ hành (%)."""
    text = soup.get_text()
    result: dict[str, float] = {}
    for hanh in ["Kim", "Mộc", "Thủy", "Hỏa", "Thổ"]:
        m = re.search(rf"{hanh}[:\s(]+([\d.]+)\s*%", text)
        if m:
            result[hanh] = float(m.group(1))
    if not result:
        for hanh in ["Kim", "Mộc", "Thủy", "Hỏa", "Thổ"]:
            m = re.search(rf"hành\s+mạnh\s+nhất\s+là\s+{hanh}\s*\(([\d.]+)%\)", text, re.IGNORECASE)
            if m:
                result[hanh] = float(m.group(1))
    return result


def _parse_dung_than(soup: BeautifulSoup) -> dict[str, str]:
    """Parse Dụng Thần, Hỉ thần, Kỵ thần."""
    text = soup.get_text()
    result: dict[str, str] = {}
    m = re.search(r"Dụng Thần[:\s]+([A-Za-zÀ-ỹ]+)", text)
    if m:
        result["dung_than"] = m.group(1).strip()
    m = re.search(r"Hỉ thần[:\s]+([A-Za-zÀ-ỹ]+)", text)
    if m:
        result["hy_than"] = m.group(1).strip()
    m = re.search(r"Kỵ thần[:\s]+([A-Za-zÀ-ỹ]+)", text)
    if m:
        result["ky_than"] = m.group(1).strip()
    return result


def _parse_thap_than(soup: BeautifulSoup) -> dict[str, str]:
    """Parse Thập Thần chính (từ bảng Tứ Trụ)."""
    tu_tru = _parse_tu_tru(soup)
    return {
        "gio": tu_tru.get("gio", {}).get("thap_than", ""),
        "ngay": tu_tru.get("ngay", {}).get("thap_than", ""),
        "thang": tu_tru.get("thang", {}).get("thap_than", ""),
        "nam": tu_tru.get("nam", {}).get("thap_than", ""),
    }


def _parse_cach_cuc(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse Cách cục đặc biệt."""
    text = soup.get_text()
    result: dict[str, Any] = {"loai": None, "mo_ta": ""}
    m = re.search(r"Cách cục đặc biệt[:\s]+([^\n.]+)", text)
    if m:
        result["loai"] = "hoa_cach" if "Hóa cách" in m.group(1) else "khac"
        result["mo_ta"] = m.group(1).strip()
    m = re.search(r"Hóa cách\s+([A-Za-zÀ-ỹ]+-[A-Za-zÀ-ỹ]+)\s+thành\s+([A-Za-zÀ-ỹ]+)", text)
    if m:
        result["loai"] = "hoa_cach"
        result["cap_hoa"] = m.group(1)
        result["hanh_moi"] = m.group(2)
    return result
