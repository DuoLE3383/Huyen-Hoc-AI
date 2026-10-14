"""Dịch + diễn giải 64 quẻ Hán văn → tiếng Việt bằng llama-server."""
import asyncio, json, sqlite3, sys, time
from pathlib import Path
import httpx

LLAMA = "http://172.31.144.1:8080"
DB = Path(__file__).parent.parent / "core" / "huyen_hoc.db"

PROMPT = """Bạn là chuyên gia Kinh Dịch. Dưới đây là nguyên văn Hán văn quẻ {que} ({ten_han}):

<hanvan>
{text}
</hanvan>

Yêu cầu:
1. Dịch + diễn giải quẻ này sang tiếng Việt (5-7 câu).
2. Liệt kê lời giải 6 hào (mỗi hào 2-3 câu).

Trả về JSON:
{{
  "que_dien_giai": "đoạn văn 5-7 câu",
  "hao": [
    {{"hao_so": 1, "noi_dung": "..."}},
    {{"hao_so": 2, "noi_dung": "..."}},
    ...đến hào 6
  ]
}}

LUÔN trả lời 100% tiếng Việt. Không markdown, chỉ JSON."""


def load_all_hanvan() -> list[tuple]:
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT que_so, ten_han, wikitext FROM kinh_dich_hanvan ORDER BY que_so").fetchall()


async def gen_one(que_so: int, ten_han: str, text: str) -> dict | None:
    # Clean wikitext
    import re
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\{\{[^}]+\}\}', '', clean)
    clean = re.sub(r'\[\[File:[^\]]+\]\]', '', clean)
    clean = re.sub(r'-{[^}]+}-', '', clean)

    prompt = PROMPT.format(que=que_so, ten_han=ten_han, text=clean[:2500])
    try:
        async with httpx.AsyncClient(timeout=180.0) as c:
            r = await c.post(f"{LLAMA}/v1/chat/completions", json={
                "messages": [
                    {"role": "system", "content": "Chuyên gia Kinh Dịch. Trả lời tiếng Việt. Chỉ JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 2000, "temperature": 0.6,
                "response_format": {"type": "json_object"},
            })
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            # Post-filter Trung + Hàn
            content = re.sub(r'[\u4e00-\u9fff\uac00-\ud7af]+', '', content)
            return json.loads(content)
    except Exception as e:
        print(f"❌ Q{que_so:02d}: {e}")
        return None


async def main(start=1, end=64):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = load_all_hanvan()
    for que_so, ten_han, text in rows:
        if not (start <= que_so <= end):
            continue
        exists = cur.execute(
            "SELECT 1 FROM kinh_dich_knowledge WHERE que_so=? AND loai='que_v2'",
            (que_so,)
        ).fetchone()
        if exists:
            print(f"· skip Q{que_so:02d} {ten_han}")
            continue
        t0 = time.time()
        data = await gen_one(que_so, ten_han, text)
        if not data:
            continue
        # Lưu quẻ
        cur.execute("""
            INSERT OR REPLACE INTO kinh_dich_knowledge
            (que_so, hao_so, loai, tieu_de, noi_dung)
            VALUES (?, NULL, 'que_v2', ?, ?)
        """, (que_so, ten_han, data.get("que_dien_giai", "")))
        # Lưu hào
        for h in data.get("hao", []):
            if not isinstance(h, dict): continue
            cur.execute("""
                INSERT OR REPLACE INTO kinh_dich_knowledge
                (que_so, hao_so, loai, tieu_de, noi_dung)
                VALUES (?, ?, 'hao_v2', ?, ?)
            """, (que_so, h.get("hao_so"), f"Hào {h.get('hao_so')} {ten_han}", h.get("noi_dung", "")))
        conn.commit()
        print(f"✅ Q{que_so:02d} {ten_han} ({time.time()-t0:.1f}s)")

    n = cur.execute("SELECT COUNT(*) FROM kinh_dich_knowledge WHERE loai IN ('que_v2','hao_v2')").fetchone()[0]
    print(f"\n✅ Total {n} rows v2")
    conn.close()


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    e = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    asyncio.run(main(s, e))
