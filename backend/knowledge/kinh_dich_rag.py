"""RAG Kinh Dịch: ưu tiên v2 (dịch Hán văn), fallback v1 (LLM sinh)."""
import json, sqlite3
from knowledge.nguyen_hien_le_cache import get_context_for_que
from pathlib import Path
from functools import lru_cache

DB_PATH = Path(__file__).parent.parent / "core" / "huyen_hoc.db"


import re


def _conn():
    return sqlite3.connect(DB_PATH)


@lru_cache(maxsize=1)
def _load_all() -> dict[int, dict]:
    """Load tất cả quẻ + hào (ưu tiên v2)."""
    data: dict[int, dict] = {}
    try:
        with _conn() as c:
            # 1. Lấy quẻ v2 (dịch từ Hán văn) — CHỈ dùng nếu noi_dung đủ dài
            rows_v2 = c.execute("""
                SELECT que_so, tieu_de, noi_dung, metadata_json
                FROM kinh_dich_knowledge
                WHERE loai='que_v2'
            """).fetchall()
            import re
            for q, ten, text, meta in rows_v2:
                clean = re.sub(r'[\s，。、《》「」『』【】；：！？、,.]+', '', text or "")
                if len(clean) < 30:  # quá ngắn → bỏ qua, fallback v1
                    continue
                data[q] = {"que_so": q, "ten_que": ten or "", "theme": "", "dien_giai": text or "", "_has_v2": True}

            # 2. Fallback v1 cho quẻ chưa có v2
            rows_v1 = c.execute("""
                SELECT que_so, tieu_de, noi_dung, metadata_json
                FROM kinh_dich_knowledge
                WHERE loai='que'
            """).fetchall()
            for q, ten, text, meta in rows_v1:
                theme = ""
                try:
                    theme = json.loads(meta or "{}").get("theme", "")
                except Exception:
                    pass
                if q not in data:
                    # Chưa có v2 → dùng v1 làm chính
                    data[q] = {"que_so": q, "ten_que": ten or "", "theme": theme, "dien_giai": text or ""}
                else:
                    # Có v2 → override tên + theme từ v1
                    data[q]["ten_que"] = ten or data[q].get("ten_que", "")
                    data[q]["theme"] = theme

            # 3. Load hào (v2 ưu tiên, fallback v1)
            for q in data:
                def is_valid(text):
                    if not text: return False
                    clean = re.sub(r'[\s，。、《》「」『』【】；：！？、,.]+', '', text)
                    return len(clean) >= 15

                hao_v2 = c.execute("""
                    SELECT hao_so, noi_dung FROM kinh_dich_knowledge
                    WHERE que_so=? AND loai='hao_v2' ORDER BY hao_so
                """, (q,)).fetchall()
                hao_v2 = [(h[0], h[1]) for h in hao_v2 if is_valid(h[1])]

                if len(hao_v2) < 6:
                    hao_v1 = c.execute("""
                        SELECT hao_so, noi_dung FROM kinh_dich_knowledge
                        WHERE que_so=? AND loai='hao' ORDER BY hao_so
                    """, (q,)).fetchall()
                    hao_v2 = [(h[0], h[1]) for h in hao_v1 if is_valid(h[1])]

                data[q]["hao"] = [{"hao_so": h[0], "noi_dung": h[1]} for h in hao_v2 if h[0]]
    except Exception as e:
        print(f"⚠️  kinh_dich_rag: {e}")
    return data


def get_que(que_so: int) -> dict | None:
    return _load_all().get(que_so)


def get_context(que_chinh_so: int, que_bien_so: int) -> str:
    """Format context cho prompt — có cả 6 hào từ."""
    parts = []
    for label, so in [("QUẺ CHÍNH", que_chinh_so), ("QUẺ BIẾN", que_bien_so)]:
        q = get_que(so)
        if not q:
            continue
        text = f"### {label}: Quẻ {q['que_so']} — {q['ten_que']}\n"
        if q.get("theme"):
            text += f"**Chủ đề:** {q['theme']}\n"
        text += f"\n{q['dien_giai']}\n"
        hao_list = q.get("hao", [])
        if hao_list:
            text += "\n**Hào từ:**\n"
            for h in hao_list:
                text += f"- Hào {h['hao_so']}: {h['noi_dung']}\n"
        parts.append(text)

        # ── Bổ sung context Nguyễn Hiến Lê (nếu có cache) ──
        try:
            nhl = get_context_for_que(so)
            if nhl:
                parts.append(nhl)
        except Exception:
            pass

    return "\n---\n".join(parts)


def clear_cache():
    """Gọi khi DB thay đổi (buộc reload lần sau)."""
    _load_all.cache_clear()
