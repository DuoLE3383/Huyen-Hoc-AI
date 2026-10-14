"""Đọc cache quẻ từ hocvienlyso.org (Nguyễn Hiến Lê).
Frontend dùng nguyên văn Hán + Hán-Việt. Backend dùng Hán-Việt cho LLM.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "kinh_dich" / "hocvienlyso"


def load_que(so: int) -> dict[str, Any] | None:
    f = CACHE_DIR / f"que-{so:02d}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def format_for_frontend(so: int) -> dict[str, Any] | None:
    """Trả nguyên văn Hán + Hán-Việt + Dịch + Giảng cho frontend."""
    d = load_que(so)
    if not d:
        return None
    return {
        "que_so": so,
        "title": d.get("title", ""),
        "ten_han": d.get("ten_han", ""),
        "thoan_tu": d.get("thoan_tu", {}),
        "hao_tu": d.get("hao_tu", []),
        "dai_y": d.get("dai_y", ""),
    }


def format_for_prompt(so: int) -> str:
    """Trả Hán-Việt + Dịch cho LLM (không Hán tự để tiết kiệm token)."""
    d = load_que(so)
    if not d:
        return ""
    lines = [f"### Quẻ {so}: {d.get('title', '')}"]
    tt = d.get("thoan_tu", {})
    if tt.get("han_viet"):
        lines.append(f"**Thoán từ:** {tt['han_viet']}")
    if tt.get("dich"):
        lines.append(f"**Dịch:** {tt['dich']}")
    if tt.get("giang"):
        lines.append(f"**Giảng:** {tt['giang'][:500]}")
    for h in d.get("hao_tu", []):
        lines.append(f"\n**Hào {h['so']} ({h['ten_han']}):** {h.get('han_viet', '')}")
        if h.get("dich"):
            lines.append(f"  Dịch: {h['dich'][:300]}")
    return "\n".join(lines)
