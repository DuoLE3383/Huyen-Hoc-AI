"""Crawl 64 quẻ Hán văn từ Wikisource — action=raw."""
import sqlite3, sys, time
from pathlib import Path
import httpx

DB = Path(__file__).parent.parent / "core" / "huyen_hoc.db"
HEADERS = {"User-Agent": "HuyenHocAI/1.0 (educational)"}

QUE_HAN = [
    "乾","坤","屯","蒙","需","讼","师","比","小畜","履","泰","否","同人","大有","谦","豫",
    "随","蛊","临","观","噬嗑","贲","剥","复","无妄","大畜","颐","大过","坎","离","咸","恒",
    "遁","大壮","晋","明夷","家人","睽","蹇","解","损","益","夬","姤","萃","升","困","井",
    "革","鼎","震","艮","渐","归妹","丰","旅","巽","兑","涣","节","中孚","小过","既济","未济",
]


def fetch(que_han: str) -> str | None:
    url = f"https://zh.wikisource.org/wiki/周易/{que_han}?action=raw"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"❌ {que_han}: {e}")
        return None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kinh_dich_hanvan (
            que_so INTEGER PRIMARY KEY,
            ten_han TEXT NOT NULL,
            wikitext TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    for i, que_han in enumerate(QUE_HAN, start=1):
        exists = cur.execute("SELECT 1 FROM kinh_dich_hanvan WHERE que_so=?", (i,)).fetchone()
        if exists:
            print(f"· skip {i:02d} {que_han}")
            continue
        text = fetch(que_han)
        if text:
            cur.execute(
                "INSERT OR REPLACE INTO kinh_dich_hanvan (que_so, ten_han, wikitext) VALUES (?,?,?)",
                (i, que_han, text)
            )
            conn.commit()
            print(f"✅ {i:02d} {que_han} ({len(text)} chars)")
        time.sleep(1)

    n = cur.execute("SELECT COUNT(*) FROM kinh_dich_hanvan").fetchone()[0]
    print(f"\n✅ Total {n}/64")
    conn.close()


if __name__ == "__main__":
    main()
