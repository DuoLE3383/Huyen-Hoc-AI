"""RAG cho Kinh Dịch: load 64 quẻ từ data/knowledge/kinh_dich/."""
import json
from pathlib import Path
from functools import lru_cache

KB_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "kinh_dich"

@lru_cache(maxsize=1)
def _load_all() -> dict[int, dict]:
    """Load tất cả 64 quẻ 1 lần, cache."""
    data = {}
    for f in sorted(KB_DIR.glob("que-*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            data[d["que_so"]] = d
        except Exception:
            continue
    return data

def get_que(que_so: int) -> dict | None:
    """Lấy data 1 quẻ."""
    return _load_all().get(que_so)

def get_context(que_chinh_so: int, que_bien_so: int) -> str:
    """Format context cho prompt LLM."""
    parts = []
    for label, so in [("QUẺ CHÍNH", que_chinh_so), ("QUẺ BIẾN", que_bien_so)]:
        q = get_que(so)
        if not q:
            continue
        parts.append(f"""### {label}: Quẻ {q['que_so']} — {q['ten_que']}
**Chủ đề:** {q['theme']}

{q['dien_giai']}
""")
    return "\n---\n".join(parts)
