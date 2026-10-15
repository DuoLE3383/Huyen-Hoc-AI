"""Cache Bát Tự — SQLite, TTL vĩnh viễn (Bát Tự không đổi theo thời gian)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

CACHE_DB = Path("data/bat_tu_cache.db")


def _ensure_dir() -> None:
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)


def init_cache() -> None:
    """Khởi tạo bảng cache (idempotent)."""
    _ensure_dir()
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bat_tu_cache (
            cache_key TEXT PRIMARY KEY,
            ngay_sinh TEXT NOT NULL,
            gio_sinh TEXT NOT NULL,
            gioi_tinh TEXT NOT NULL,
            data_json TEXT NOT NULL,
            nguon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ngay_gio ON bat_tu_cache(ngay_sinh, gio_sinh, gioi_tinh)")
    conn.commit()
    conn.close()


def make_cache_key(ngay_sinh: str, gio_sinh: str, gioi_tinh: str) -> str:
    """Tạo cache key ổn định từ thông tin sinh."""
    raw = f"{ngay_sinh}|{gio_sinh}|{gioi_tinh}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def get_cache(cache_key: str) -> Optional[dict[str, Any]]:
    """Lấy cache theo key. Tự động cập nhật last_accessed + access_count."""
    _ensure_dir()
    conn = sqlite3.connect(CACHE_DB)
    row = conn.execute(
        "SELECT data_json FROM bat_tu_cache WHERE cache_key = ?",
        (cache_key,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE bat_tu_cache SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE cache_key = ?",
            (cache_key,)
        )
        conn.commit()
    conn.close()
    return json.loads(row[0]) if row else None


def set_cache(
    cache_key: str,
    ngay_sinh: str,
    gio_sinh: str,
    gioi_tinh: str,
    data: dict[str, Any],
    nguon: str,
) -> None:
    """Lưu cache — INSERT OR REPLACE (không TTL, vĩnh viễn)."""
    _ensure_dir()
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        """INSERT OR REPLACE INTO bat_tu_cache
           (cache_key, ngay_sinh, gio_sinh, gioi_tinh, data_json, nguon, created_at, last_accessed, access_count)
           VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)""",
        (cache_key, ngay_sinh, gio_sinh, gioi_tinh, json.dumps(data, ensure_ascii=False), nguon)
    )
    conn.commit()
    conn.close()


def get_cache_stats() -> dict[str, Any]:
    """Thống kê cache — dùng cho debug."""
    _ensure_dir()
    conn = sqlite3.connect(CACHE_DB)
    total = conn.execute("SELECT COUNT(*) FROM bat_tu_cache").fetchone()[0]
    by_source = conn.execute(
        "SELECT nguon, COUNT(*) FROM bat_tu_cache GROUP BY nguon"
    ).fetchall()
    top = conn.execute(
        "SELECT ngay_sinh, gio_sinh, gioi_tinh, access_count FROM bat_tu_cache ORDER BY access_count DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "by_source": dict(by_source),
        "top_accessed": [
            {"ngay_sinh": r[0], "gio_sinh": r[1], "gioi_tinh": r[2], "access_count": r[3]}
            for r in top
        ],
    }
