"""Sinh 384 hào từ (64 quẻ × 6 hào) — lưu vào SQLite."""
import asyncio, sqlite3, sys, time
from pathlib import Path
import httpx

LLAMA = "http://172.31.144.1:8080"
MODEL = "qwen2.5:7b"
DB = Path(__file__).parent.parent / "core" / "huyen_hoc.db"

PROMPT = """Viết lời giải hào {hao} của quẻ số {que} — {ten_que} (chủ đề: {theme}).

Yêu cầu (tiếng Việt, 4-6 câu):
- Tình huống cụ thể ứng với hào này.
- Cát hay hung? Nên hay không nên làm gì?
- Ứng dụng thực tế cho công việc, sức khỏe, tình cảm.

Chỉ trả về đoạn văn, không markdown, không tiêu đề."""


def load_que(que_so: int) -> dict:
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT tieu_de, noi_dung, metadata_json FROM kinh_dich_knowledge WHERE que_so=? AND loai='que'",
            (que_so,)
        ).fetchone()
        if not row:
            return None
        import json
        theme = ""
        try:
            theme = json.loads(row[2] or "{}").get("theme", "")
        except Exception:
            pass
        return {"ten_que": row[0], "theme": theme}


async def gen_one(que: int, ten: str, theme: str, hao: int) -> str:
    prompt = PROMPT.format(hao=hao, que=que, ten_que=ten, theme=theme)
    async with httpx.AsyncClient(timeout=180.0) as c:
        r = await c.post(f"{LLAMA}/v1/chat/completions", json={
            "messages": [
                {"role": "system", "content": "Trả lời 100% bằng tiếng Việt, không markdown."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.7,
        })
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def main(start=1, end=64):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    done = 0
    for q in range(start, end + 1):
        info = load_que(q)
        if not info:
            print(f"❌ Quẻ {q} chưa có trong DB")
            continue
        for hao in range(1, 7):
            exists = cur.execute(
                "SELECT 1 FROM kinh_dich_knowledge WHERE que_so=? AND hao_so=? AND loai='hao'",
                (q, hao)
            ).fetchone()
            if exists:
                continue
            t0 = time.time()
            try:
                text = await gen_one(q, info["ten_que"], info["theme"], hao)
                cur.execute("""
                    INSERT OR REPLACE INTO kinh_dich_knowledge
                    (que_so, hao_so, loai, tieu_de, noi_dung)
                    VALUES (?, ?, 'hao', ?, ?)
                """, (q, hao, f"Hào {hao} quẻ {info['ten_que']}", text))
                conn.commit()
                done += 1
                print(f"✅ Q{q:02d} H{hao} ({time.time()-t0:.1f}s)")
            except Exception as e:
                print(f"❌ Q{q:02d} H{hao}: {e}")
    print(f"\n✅ Total {done} hào mới")
    conn.close()


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    e = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    asyncio.run(main(s, e))
