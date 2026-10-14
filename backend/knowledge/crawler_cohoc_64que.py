"""
Crawl 64 quẻ Kinh Dịch từ cohoc.net
Nguồn: "Kinh Dịch - Đạo của người quân tử" — Nguyễn Hiến Lê

Output: backend/data/knowledge/kinh_dich/nguyen_hien_le/que-NN.json
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import unicodedata

import httpx
from bs4 import BeautifulSoup

BASE = "https://cohoc.net"
INDEX_URL = f"{BASE}/64-que-dich.html"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "kinh_dich" / "nguyen_hien_le"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.9",
}


async def fetch_index(client: httpx.AsyncClient) -> list[dict]:
    r = await client.get(INDEX_URL, headers=HEADERS, timeout=30.0)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items: list[dict] = []
    for h3 in soup.find_all("h3"):
        a = h3.find("a", href=re.compile(r"kid-\d+\.html"))
        if not a:
            continue
        m = re.search(r"Quẻ\s+(\d+)\s*[:.]\s*(.+)", a.get_text(strip=True))
        if not m:
            continue
        items.append({
            "so": int(m.group(1)),
            "ten": unicodedata.normalize("NFC", m.group(2).strip()),
            "url": f"{BASE}/{a['href']}",
        })
    items.sort(key=lambda x: x["so"])
    return items


def parse_que(html: str, so: int, ten: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    title = unicodedata.normalize("NFC", h1.get_text(strip=True)) if h1 else f"QUẺ {so}: {ten}"

    nd = soup.find("div", class_="noi-dung")
    if not nd:
        return {
            "so": so, "ten": ten, "url": url,
            "title": title, "que_tu": [], "hao_tu": [],
            "raw_len": len(html),
            "source": "Nguyễn Hiến Lê — Kinh Dịch: Đạo của người quân tử",
        }

    blocks: list[dict] = []
    for el in nd.find_all(["p", "ul"], recursive=False):
        if el.name == "ul":
            for li in el.find_all("li"):
                txt = unicodedata.normalize("NFC", li.get_text(" ", strip=True))
                blocks.append({"text": txt, "kind": "li"})
            continue

        strong = el.find("strong")
        bold_label = strong.get_text(strip=True).rstrip(":") if strong else None
        text = unicodedata.normalize("NFC", el.get_text(" ", strip=True))
        if not text:
            continue
        bold_label = unicodedata.normalize("NFC", bold_label) if bold_label else None
        blocks.append({"text": text, "kind": "p", "bold": bold_label})

    que_tu_blocks: list[dict] = []
    hao_tu_blocks: list[dict] = []
    in_hao_section = False

    for b in blocks:
        txt = b["text"]
        txt_lc = txt.lower()
        bold_lc = (b.get("bold") or "").lower()

        # Bắt đầu section hào từ khi gặp:
        #   - <p><strong>Hào từ:</strong></p>  (bold = "hào từ")
        #   - hoặc câu "Từ đây trở xuống là Hào từ, ..."
        starts_hao = (
            bold_lc in ("hào từ", "hào tự") or
            ("từ đây trở xuống" in txt_lc and "hào" in txt_lc)
        )
        if starts_hao:
            in_hao_section = True
            continue

        if not in_hao_section:
            que_tu_blocks.append(b)
        else:
            hao_tu_blocks.append(b)

    return {
        "so": so,
        "ten": ten,
        "url": url,
        "title": title,
        "que_tu": que_tu_blocks,
        "hao_tu": hao_tu_blocks,
        "raw_len": len(html),
        "source": "Nguyễn Hiến Lê — Kinh Dịch: Đạo của người quân tử",
    }


async def fetch_que(client: httpx.AsyncClient, item: dict, idx: int, total: int) -> dict | None:
    try:
        headers = dict(HEADERS)
        headers["Referer"] = INDEX_URL
        r = await client.get(item["url"], headers=headers, timeout=30.0)
        r.raise_for_status()
        data = parse_que(r.text, item["so"], item["ten"], item["url"])
        print(f"  [{idx}/{total}] ✅ Quẻ {item['so']:>2} {item['ten']}  "
              f"({len(data['que_tu'])} quẻ từ, {len(data['hao_tu'])} hào từ)")
        return data
    except Exception as e:
        print(f"  [{idx}/{total}] ❌ Quẻ {item['so']:>2} {item['ten']} — {e}")
        return None


async def main():
    import sys as _sys

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resume = "--resume" in _sys.argv

    # limit=5 để tránh redirect loop vô hạn
    async with httpx.AsyncClient(
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        items = await fetch_index(client)
        print(f"📋 Tìm thấy {len(items)} quẻ trong index\n")
        if len(items) < 60:
            print(f"⚠️  Cảnh báo: chỉ tìm thấy {len(items)} quẻ")

        ok, skip, fail = 0, 0, 0
        for i, item in enumerate(items, 1):
            out = OUT_DIR / f"que-{item['so']:02d}.json"

            # Resume: bỏ qua quẻ đã crawl
            if resume and out.exists() and out.stat().st_size > 1000:
                skip += 1
                print(f"  [{i}/{len(items)}] ⏭  Quẻ {item['so']:>2} {item['ten']} (đã có)")
                continue

            # Retry 3 lần
            data = None
            for attempt in range(1, 4):
                data = await fetch_que(client, item, i, len(items))
                if data:
                    break
                wait = 3.0 * attempt
                print(f"      ↩ Retry {attempt}/3 sau {wait}s...")
                await asyncio.sleep(wait)

            if data:
                out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                ok += 1
            else:
                fail += 1

            # Sleep lâu hơn để tránh rate limit
            await asyncio.sleep(2.5)

    print(f"\n✅ Hoàn tất: {ok} OK, {skip} bỏ qua, {fail} thất bại")
    print(f"📁 Output: {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
