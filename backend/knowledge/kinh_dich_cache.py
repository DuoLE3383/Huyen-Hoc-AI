"""Cache kết quả luận giải Kinh Dịch."""
import hashlib, json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data" / "kinh_dich_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _key(qc: int, qb: int, q: str) -> Path:
    norm = " ".join(q.lower().strip().split())
    h = hashlib.sha256(f"{qc}|{qb}|{norm}".encode()).hexdigest()[:20]
    return CACHE_DIR / f"{h}.json"


def get(qc: int, qb: int, q: str) -> dict | None:
    f = _key(qc, qb, q)
    if not f.exists(): return None
    try: return json.loads(f.read_text(encoding="utf-8"))
    except: return None


def save(qc: int, qb: int, q: str, data: dict) -> None:
    try: _key(qc, qb, q).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except: pass
