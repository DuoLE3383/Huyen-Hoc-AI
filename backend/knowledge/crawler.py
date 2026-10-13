"""
Crawler cho tuvi.cohoc.net — có rate limit, retry, skip duplicates.
Tự động chờ khi bị limit.
"""
import httpx
import time
import re
import json
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime


BASE_URL = "https://tuvi.cohoc.net"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "tu_vi"
CACHE_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "cache"
STATE_FILE = Path(__file__).parent.parent / "data" / "knowledge" / "crawl_state.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (compatible; HuyenBaoBot/1.0; "
    "+https://huyenbao.com/bot; contact@huyenbao.com)"
)

# Cấu hình retry
MAX_RETRIES = 3
RETRY_DELAY_BASE = 30          # 30s, 60s, 120s (exponential)
RATE_LIMIT_WAIT = 600          # 10 phút khi bị 429/403
DEFAULT_DELAY = 3           # 3s giữa các request bình thường
    

class CrawlState:
    """Quản lý state: URLs đã crawl, lỗi, lần chạy cuối"""

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "completed": [],      # URLs crawl thành công
            "failed": {},         # {url: {"error": ..., "attempts": N}}
            "last_run": None,
            "total_crawled": 0,
        }

    def save(self):
        self.state["last_run"] = datetime.now().isoformat()
        self.state_file.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def is_completed(self, url: str) -> bool:
        return url in self.state["completed"]

    def mark_completed(self, url: str):
        if url not in self.state["completed"]:
            self.state["completed"].append(url)
            self.state["total_crawled"] += 1
        self.state["failed"].pop(url, None)
        self.save()

    def mark_failed(self, url: str, error: str):
        entry = self.state["failed"].get(url, {"attempts": 0})
        entry["attempts"] += 1
        entry["error"] = error
        entry["last_attempt"] = datetime.now().isoformat()
        self.state["failed"][url] = entry
        self.save()

    def get_stats(self) -> Dict:
        return {
            "completed": len(self.state["completed"]),
            "failed": len(self.state["failed"]),
            "total": self.state["total_crawled"],
        }


class TuViCrawler:
    def __init__(self, respect_robots: bool = True, delay: float = DEFAULT_DELAY):
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        )
        self.respect_robots = respect_robots
        self.delay = delay
        self.robot_parser = None
        self.state = CrawlState()

        # Session stats
        self.session_stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "rate_limited": 0,
        }

        if respect_robots:
            self._load_robots()

    def _load_robots(self):
        try:
            rp = RobotFileParser()
            rp.set_url(f"{BASE_URL}/robots.txt")
            rp.read()
            self.robot_parser = rp
            print("✅ Đã load robots.txt")
        except Exception as e:
            print(f"⚠️  Không load được robots.txt: {e}")
            self.robot_parser = None

    def can_fetch(self, url: str) -> bool:
        if not self.respect_robots or not self.robot_parser:
            return True
        return self.robot_parser.can_fetch(USER_AGENT, url)

    def _slugify(self, url: str) -> str:
        """Tạo filename từ URL"""
        path = urlparse(url).path.strip("/")
        slug = path.replace("/", "_").replace(".html", "")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
        return f"{slug}.md" if slug else "index.md"

    def _should_skip(self, url: str) -> bool:
        """Check nếu URL đã crawl hoặc file đã tồn tại"""
        # Đã crawl thành công
        if self.state.is_completed(url):
            return True

        # File .md đã tồn tại
        filename = self._slugify(url)
        filepath = OUTPUT_DIR / filename
        if filepath.exists() and filepath.stat().st_size > 500:
            # Đánh dấu là completed để lần sau skip luôn
            self.state.mark_completed(url)
            return True

        return False

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """
        Fetch URL với retry logic + xử lý rate limit.
        Return HTML text hoặc None nếu fail.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"   🌐 GET {url[:80]}... (attempt {attempt}/{MAX_RETRIES})")
                r = self.client.get(url)

                # === Xử lý rate limit ===
                if r.status_code in (429, 403, 503):
                    wait_time = RATE_LIMIT_WAIT
                    print(f"   ⏸️  Bị limit (HTTP {r.status_code})")
                    print(f"   ⏳ Chờ {wait_time // 60} phút rồi tiếp tục...")
                    self.session_stats["rate_limited"] += 1

                    # Đếm ngược cho đẹp
                    for remaining in range(wait_time, 0, -30):
                        print(f"      Còn {remaining // 60}m{remaining % 60}s...", end="\r")
                        time.sleep(min(30, remaining))
                    print()
                    continue  # Retry sau khi chờ

                # === Xử lý lỗi khác ===
                if r.status_code == 404:
                    print(f"   ❌ 404 Not Found — skip")
                    return None

                r.raise_for_status()
                return r.text

            except httpx.TimeoutException:
                print(f"   ⏱️  Timeout (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                    print(f"   ⏳ Chờ {delay}s rồi retry...")
                    time.sleep(delay)
                else:
                    return None

            except httpx.HTTPStatusError as e:
                print(f"   ❌ HTTP {e.response.status_code}")
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_BASE * attempt
                    time.sleep(delay)
                else:
                    return None

            except Exception as e:
                print(f"   ❌ Lỗi: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_BASE * attempt)
                else:
                    return None

        return None

    def crawl_page(self, url: str, use_cache: bool = True) -> Dict:
        """Crawl 1 trang với skip + retry"""
        # === Skip nếu đã crawl ===
        if self._should_skip(url):
            print(f"   ⏭️  Skip (đã có): {url[:70]}")
            self.session_stats["skipped"] += 1
            return {"url": url, "skipped": True}

        # === Check robots ===
        if not self.can_fetch(url):
            print(f"   🚫 Robots.txt disallow: {url[:70]}")
            self.session_stats["skipped"] += 1
            self.state.mark_failed(url, "robots_disallow")
            return {"error": "Disallowed by robots.txt", "url": url}

        # === Check cache ===
        cache_file = CACHE_DIR / f"{self._slugify(url).replace('.md', '.html')}"
        html = None

        if use_cache and cache_file.exists():
            print(f"   📦 Cache hit: {url[:70]}")
            html = cache_file.read_text(encoding="utf-8")
            self.session_stats["skipped"] += 1

        # === Fetch với retry ===
        if html is None:
            html = self._fetch_with_retry(url)
            if html is None:
                print(f"   ❌ Bỏ qua sau {MAX_RETRIES} lần thử: {url[:70]}")
                self.session_stats["failed"] += 1
                self.state.mark_failed(url, "fetch_failed")
                return {"error": "Fetch failed", "url": url}

            # Save cache
            try:
                cache_file.write_text(html, encoding="utf-8")
            except Exception:
                pass

        # === Parse HTML ===
        try:
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.find("h1") or soup.find("title")
            title = title_el.get_text(strip=True) if title_el else "Không rõ"

            # Tìm content container
            content_el = None
            for sel in [
                "article", "main", ".content", "#content",
                ".post-content", ".entry-content", ".luan-giai",
                ".news-content", ".detail-content",
            ]:
                content_el = soup.select_one(sel)
                if content_el:
                    break

            if not content_el:
                content_el = soup.body or soup

            # Clean noise
            for tag in content_el.find_all([
                "script", "style", "nav", "footer", "header",
                "aside", "iframe", "noscript", "form",
            ]):
                tag.decompose()

            for tag in content_el.find_all(class_=re.compile(
                r"ads|banner|comment|sidebar|menu|nav|footer|related"
            )):
                tag.decompose()

            # Extract text
            text = content_el.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)

            self.session_stats["success"] += 1
            self.state.mark_completed(url)

            return {
                "url": url,
                "title": title,
                "text": text,
                "word_count": len(text.split()),
                "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        except Exception as e:
            print(f"   ❌ Parse lỗi: {e}")
            self.session_stats["failed"] += 1
            self.state.mark_failed(url, f"parse_error: {e}")
            return {"error": f"Parse error: {e}", "url": url}

    def save_page(self, page: Dict, filename: str = None) -> Optional[Path]:
        """Lưu page thành markdown có frontmatter"""
        if "error" in page or page.get("skipped"):
            return None

        if not filename:
            filename = self._slugify(page["url"])

        filepath = OUTPUT_DIR / filename

        # Nếu đã tồn tại → skip
        if filepath.exists() and filepath.stat().st_size > 500:
            print(f"   💾 Đã tồn tại: {filepath.name}")
            return filepath

        safe_title = page["title"].replace('"', '\\"')

        content = f"""---
title: "{safe_title}"
url: {page['url']}
crawled_at: {page['crawled_at']}
word_count: {page['word_count']}
source: tuvi.cohoc.net
license: Tử Vi Đẩu Số Tân Biên — Vân Đằng Thái Thứ Lang
usage: Chỉ dùng làm knowledge base cho AI RAG, không copy nguyên văn cho user
---

# {page['title']}

{page['text']}
"""

        try:
            filepath.write_text(content, encoding="utf-8")
            print(f"   💾 Saved: {filepath.name} ({page['word_count']} từ)")
            return filepath
        except Exception as e:
            print(f"   ❌ Lỗi save: {e}")
            return None

    def crawl_list(self, urls: List[str]) -> List[Path]:
        """
        Crawl list URLs với:
        - Skip duplicates
        - Retry on error
        - Chờ 10 phút khi bị limit
        """
        results = []
        total = len(urls)

        # Pre-check skip
        to_crawl = [u for u in urls if not self._should_skip(u)]
        already_have = total - len(to_crawl)

        print(f"\n{'=' * 60}")
        print(f"📋 KẾ HOẠCH CRAWL")
        print(f"{'=' * 60}")
        print(f"   📊 Tổng URLs:      {total}")
        print(f"   ✅ Đã có sẵn:       {already_have}")
        print(f"   🔄 Cần crawl mới:  {len(to_crawl)}")
        print(f"{'=' * 60}\n")

        if not to_crawl:
            print("✅ Tất cả URLs đã được crawl trước đó!")
            return results

        # === CRAWL LOOP ===
        for i, url in enumerate(to_crawl, 1):
            print(f"\n[{i}/{len(to_crawl)}]", end=" ")
            start = time.time()

            page = self.crawl_page(url)

            if page.get("skipped"):
                print(f"   ⏭️  Bỏ qua (đã có)")

            elif "error" not in page:
                path = self.save_page(page)
                if path:
                    results.append(path)

            elapsed = time.time() - start
            print(f"   ⏱️  {elapsed:.1f}s")

            # Delay giữa các request
            if i < len(to_crawl):
                time.sleep(self.delay)

        return results

    def print_stats(self):
        """In thống kê"""
        stats = self.state.get_stats()
        print("\n" + "=" * 60)
        print("📊 CRAWLER STATS")
        print("=" * 60)
        print(f"   Session:")
        print(f"      ✅ Success:        {self.session_stats['success']}")
        print(f"      ⏭️  Skipped:        {self.session_stats['skipped']}")
        print(f"      ❌ Failed:         {self.session_stats['failed']}")
        print(f"      ⏸️  Rate limited:   {self.session_stats['rate_limited']}")
        print(f"   Cumulative (all time):")
        print(f"      📦 Completed:      {stats['completed']}")
        print(f"      ⚠️  Failed:         {stats['failed']}")
        print(f"      📈 Total crawled:  {stats['total']}")
        print(f"   📁 Output: {OUTPUT_DIR}")
        print("=" * 60)


# === SỬ DỤNG ===
if __name__ == "__main__":
    crawler = TuViCrawler(respect_robots=True, delay=2.5)

    urls = [
        "https://tuvi.cohoc.net/luan-giai-cung-tat-ach-nid-1242.html",
    ]

    print("🚀 Bắt đầu crawl...")
    results = crawler.crawl_list(urls)
    crawler.print_stats()

    print(f"\n✅ Crawled {len(results)} trang mới")