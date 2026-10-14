"""
Đọc cache 64 quẻ Nguyễn Hiến Lê từ cohoc.net.
Dùng để bổ sung context cho kinh_dich_rag.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "kinh_dich" / "nguyen_hien_le"


def load_que(so: int) -> dict[str, Any] | None:
    """Đọc 1 quẻ từ cache. Trả None nếu chưa crawl."""
    f = CACHE_DIR / f"que-{so:02d}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def format_que_context(so: int, max_que_chars: int = 700, max_hao_chars: int = 300) -> str:
    """
    Format quẻ thành context ngắn gọn để đưa vào prompt.
    Chỉ lấy phần tinh túy: tên quẻ, giải nghĩa, giảng (quẻ từ) + 6 hào từ đầu.
    """
    data = load_que(so)
    if not data:
        return ""

    lines: list[str] = []
    lines.append(f"### Quẻ {data['so']} — {data['ten']} (Nguyễn Hiến Lê)")
    lines.append("")

    # Quẻ từ: lọc chỉ giữ Giải nghĩa, Dịch, Giảng
    que_keep_keys = {"giải nghĩa", "dịch", "giảng"}
    que_buf: list[str] = []
    for b in data.get("que_tu", []):
        txt = b.get("text", "").strip()
        if not txt:
            continue
        bold = (b.get("bold") or "").lower()
        # Bỏ dòng Hán tự thuần, bỏ "* Nội quái/Ngoại quái"
        if txt.startswith(("初", "九", "上", "用")):
            continue
        if txt.startswith("*"):
            continue
        if bold in que_keep_keys or not que_buf:
            que_buf.append(txt)

    que_text = "\n".join(que_buf)[:max_que_chars]
    lines.append("**Quẻ từ (lời giảng Nguyễn Hiến Lê):**")
    lines.append(que_text)
    lines.append("")

    # Hào từ: lấy tối đa 6 hào đầu, mỗi hào gộp từ khoá
    hao_buf: list[str] = []
    curr_hao: list[str] = []
    hao_count = 0

    for b in data.get("hao_tu", []):
        txt = b.get("text", "").strip()
        if not txt:
            continue
        bold = (b.get("bold") or "").lower()

        # Bắt đầu hào mới khi gặp bold là "sơ cửu", "cửu nhị", etc.
        if bold and any(k in bold for k in ("sơ", "cửu", "lục", "thượng", "nhị", "tam", "tứ", "ngũ")):
            if curr_hao:
                hao_buf.append(" | ".join(curr_hao))
                hao_count += 1
            curr_hao = [txt]
            if hao_count >= 6:
                break
        elif bold == "dịch" or "dịch:" in txt.lower():
            curr_hao.append(txt)
        elif bold == "giảng" or "giảng:" in txt.lower():
            curr_hao.append(txt[:300])

    if curr_hao and hao_count < 6:
        hao_buf.append(" | ".join(curr_hao))

    if hao_buf:
        lines.append("**Hào từ (6 hào):**")
        lines.append("\n".join(hao_buf)[:max_hao_chars * 4])

    return "\n".join(lines)


def get_context_for_que(que_so: int) -> str:
    """Wrapper cho kinh_dich_rag."""
    return format_que_context(que_so)
