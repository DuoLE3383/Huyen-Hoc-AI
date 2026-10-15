"""Service Bát Tự — orchestrate cache + crawl + fallback.

Luồng:
1. Kiểm tra cache → nếu có, trả ngay.
2. Crawl vutruhoc.vn → nếu thành công, lưu cache + trả.
3. Nếu crawl lỗi → dùng cache cũ (nếu có).
4. Nếu không có cache cũ → raise lỗi.
"""
from __future__ import annotations

import logging
from typing import Any

from bat_tu.cache import init_cache, make_cache_key, get_cache, set_cache
from bat_tu.crawler_vutruhoc import crawl_vutruhoc, CrawlError

logger = logging.getLogger(__name__)


async def get_bat_tu(
    ngay_sinh: str,
    gio_sinh: str,
    gioi_tinh: str,
) -> dict[str, Any]:
    """Lấy Bát Tự — ưu tiên cache, sau đó crawl, fallback cache cũ."""
    init_cache()
    cache_key = make_cache_key(ngay_sinh, gio_sinh, gioi_tinh)

    # 1. Kiểm tra cache
    cached = get_cache(cache_key)
    if cached:
        logger.info(f"[bat_tu] Cache HIT cho {ngay_sinh} {gio_sinh} {gioi_tinh}")
        return {**cached, "_from_cache": True, "_nguon": cached.get("nguon", "cache")}

    logger.info(f"[bat_tu] Cache MISS — crawl vutruhoc.vn cho {ngay_sinh} {gio_sinh} {gioi_tinh}")

    # 2. Crawl
    try:
        ngay, thang, nam = map(int, ngay_sinh.split("-"))
        gio, phut = map(int, gio_sinh.split(":"))
        data = await crawl_vutruhoc(ngay, thang, nam, gio, phut, gioi_tinh)
        set_cache(cache_key, ngay_sinh, gio_sinh, gioi_tinh, data, "vutruhoc.vn")
        logger.info("[bat_tu] Crawl thành công, đã lưu cache")
        return {**data, "_from_cache": False, "_nguon": "vutruhoc.vn"}
    except CrawlError as e:
        logger.warning(f"[bat_tu] Crawl lỗi: {e}")

        # 3. Fallback: cache cũ
        cached_again = get_cache(cache_key)
        if cached_again:
            logger.info("[bat_tu] Fallback cache cũ")
            return {**cached_again, "_from_cache": True, "_nguon": cached_again.get("nguon", "cache"), "_crawl_error": str(e)}

        # 4. Không có cache → raise
        raise CrawlError(
            f"Không thể lấy Bát Tự cho {ngay_sinh} {gio_sinh} {gioi_tinh}: "
            f"crawl lỗi ({e}) và không có cache cũ."
        ) from e
