"""Trích Hán tự (Thoán từ + Hào từ) từ bảng kinh_dich_hanvan."""
from __future__ import annotations
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from pypinyin import lazy_pinyin, Style
    _HAS_PYPINYIN = True
except ImportError:
    _HAS_PYPINYIN = False

DB_PATH = Path(__file__).parent.parent / "core" / "huyen_hoc.db"


def _conn():
    return sqlite3.connect(DB_PATH)


@lru_cache(maxsize=64)
def get_hanvan(que_so: int) -> dict[str, Any]:
    """
    Lấy Hán tự cho 1 quẻ.

    Returns:
        {
            "que_so": 6,
            "ten_han": "讼",
            "thoan_tu": "訟：有孚，窒，惕，中吉，終凶...",
            "hao_tu": [
                {"vi_tri": 1, "ten_han": "初六", "text": "不永所事，小有言，終吉。"},
                ...
            ]
        }
    """
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ten_han, wikitext FROM kinh_dich_hanvan WHERE que_so = ?",
                (que_so,),
            )
            row = cur.fetchone()
    except Exception:
        return {}

    if not row:
        return {}

    ten_han, wt = row
    result: dict[str, Any] = {
        "que_so": que_so,
        "ten_han": ten_han or "",
        "thoan_tu": "",
        "hao_tu": [],
    }

    # Tìm thoán từ — pattern: '''訟'''：xxx
    # VD: *<span style="color:blue">'''訟'''：有孚，窒，惕，中吉，終凶。</span>
    m = re.search(
        r"'''" + re.escape(ten_han or "") + r"'''[：:]\s*([^<]+)",
        wt,
    )
    if m:
        result["thoan_tu"] = m.group(1).strip()

    # Tìm hào từ — pattern: 初六：xxx  hoặc  九二：xxx
    hao_pattern = re.compile(
        r"(初[六九]|九[二三四五]|六[二三四五]|上[六九]|用[六九])"
        r"[：:]\s*([^<]+)",
    )
    seen = set()
    for m in hao_pattern.finditer(wt):
        ten = m.group(1)
        if ten in seen:
            continue
        seen.add(ten)
        text = m.group(2).strip()
        # Chuyển tên Hán sang số thứ tự
        vi_tri = _hao_to_int(ten)
        if vi_tri:
            result["hao_tu"].append({
                "vi_tri": vi_tri,
                "ten_han": ten,
                "text": text,
            })

    # Sắp xếp theo vị trí
    result["hao_tu"].sort(key=lambda x: x["vi_tri"])
    return result


def _hao_to_int(ten: str) -> int | None:
    """初六 → 1, 九二 → 2, ..., 上九 → 6."""
    if ten.startswith("初"):
        return 1
    if ten.startswith("上") or ten.startswith("用"):
        return 6
    map_so = {"二": 2, "三": 3, "四": 4, "五": 5}
    for k, v in map_so.items():
        if k in ten:
            return v
    return None


def format_hanvan_for_prompt(que_so: int) -> str:
    """Format Hán tự cho prompt."""
    d = get_hanvan(que_so)
    if not d:
        return ""

    lines = [
        "### Nguyên văn Hán tự (từ Wikisource — DÙNG ĐÚNG, KHÔNG BỊA)",
        "",
        f"**Thoán từ**: {d['thoan_tu']}" if d["thoan_tu"] else "",
    ]

    if d["hao_tu"]:
        lines.append("")
        lines.append("**Hào từ**:")
        for h in d["hao_tu"]:
            lines.append(f"- {h['ten_han']}：{h['text']}")

    return "\n".join(x for x in lines if x)

def to_phien_am(han_text: str) -> str:
    """Chuyển Hán tự → phiên âm pinyin (có dấu thanh)."""
    if not han_text or not _HAS_PYPINYIN:
        return ""
    try:
        # Bỏ dấu câu, chỉ lấy chữ Hán
        chars = [c for c in han_text if "\u4e00" <= c <= "\u9fff"]
        if not chars:
            return ""
        return " ".join(lazy_pinyin("".join(chars), style=Style.TONE))
    except Exception:
        return ""


def get_hanvan_full(que_so: int) -> dict[str, Any]:
    """
    Lấy Hán tự + phiên âm cho 1 quẻ.
    Dùng cho cả backend prompt (phiên âm) lẫn frontend render (Hán).
    """
    d = get_hanvan(que_so)
    if not d:
        return {}

    result = dict(d)
    result["thoan_tu_phien_am"] = to_phien_am(d.get("thoan_tu", ""))

    hao_tu_full = []
    for h in d.get("hao_tu", []):
        item = dict(h)
        item["phien_am"] = to_phien_am(h.get("text", ""))
        hao_tu_full.append(item)
    result["hao_tu"] = hao_tu_full

    return result


def format_hanvan_for_frontend(que_so: int) -> dict[str, Any]:
    """
    Format Hán tự cho frontend render (Hán + phiên âm).
    """
    d = get_hanvan_full(que_so)
    if not d:
        return {}
    return {
        "que_so": d["que_so"],
        "ten_han": d.get("ten_han", ""),
        "thoan_tu": {
            "han": d.get("thoan_tu", ""),
            "phien_am": d.get("thoan_tu_phien_am", ""),
        },
        "hao_tu": [
            {
                "vi_tri": h["vi_tri"],
                "ten_han": h.get("ten_han", ""),
                "han": h.get("text", ""),
                "phien_am": h.get("phien_am", ""),
            }
            for h in d.get("hao_tu", [])
        ],
    }


def format_hanvan_for_prompt_v2(que_so: int) -> str:
    """
    Format Hán tự cho prompt LLM — DÙNG PHIÊN ÂM (không cần Hán).
    """
    d = get_hanvan_full(que_so)
    if not d:
        return ""

    lines = ["### Nguyên văn Kinh Dịch (phiên âm Pinyin — dùng để dịch + giảng)"]

    if d.get("thoan_tu"):
        lines.append("")
        lines.append(f"**Thoán từ (phiên âm)**: {d.get('thoan_tu_phien_am', '')}")
        lines.append(f"_(Hán: {d['thoan_tu']})_")

    if d.get("hao_tu"):
        lines.append("")
        lines.append("**Hào từ**:")
        for h in d["hao_tu"]:
            lines.append(f"- {h.get('ten_han', '')}: {h.get('phien_am', '')}")
            lines.append(f"  _(Hán: {h.get('text', '')})_")

    lines.append("")
    lines.append("**QUY TẮC**: Dịch và giảng dựa trên phiên âm trên. KHÔNG bịa Hán tự.")

    return "\n".join(lines)

