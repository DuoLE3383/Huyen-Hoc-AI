"""Crawl 64 quẻ Kinh Dịch từ nhiều nguồn."""
import httpx, re, json, time
from pathlib import Path
from bs4 import BeautifulSoup

OUT_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "kinh_dich"
CACHE_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "cache" / "kinh_dich"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HuyenBaoBot/1.0)"}
DELAY = 3

def fetch(url: str) -> str | None:
    cache_file = CACHE_DIR / re.sub(r'[^a-z0-9]+', '_', url.lower())[:120]
    cache_file = cache_file.with_suffix(".html")
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    try:
        r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        r.raise_for_status()
        cache_file.write_text(r.text, encoding="utf-8")
        time.sleep(DELAY)
        return r.text
    except Exception as e:
        print(f"❌ {url}: {e}")
        return None

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

if __name__ == "__main__":
    print("Skeleton ready. Chờ URL pattern.")
