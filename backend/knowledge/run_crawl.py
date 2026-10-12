"""
Crawl toàn bộ tuvi.cohoc.net — chạy 1 lần.
Tự động skip URLs đã có, retry khi lỗi, chờ 10 phút khi bị limit.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent để import
sys.path.insert(0, str(Path(__file__).parent))

from crawler import TuViCrawler, CrawlState


# Danh sách URL tường minh
URLS_TO_CRAWL = [
    # ===== 12 CUNG =====
    "https://tuvi.cohoc.net/luan-giai-cung-menh-nid-1238.html",
    "https://tuvi.cohoc.net/luan-giai-cung-phu-mau-nid-1239.html",
    "https://tuvi.cohoc.net/luan-giai-cung-phuc-duc-nid-1240.html",
    "https://tuvi.cohoc.net/luan-giai-cung-dien-trach-nid-1241.html",
    "https://tuvi.cohoc.net/luan-giai-cung-tat-ach-nid-1242.html",
    "https://tuvi.cohoc.net/luan-giai-cung-quan-loc-nid-1243.html",
    "https://tuvi.cohoc.net/luan-giai-cung-no-boc-nid-1244.html",
    "https://tuvi.cohoc.net/luan-giai-cung-thien-di-nid-1245.html",
    "https://tuvi.cohoc.net/luan-giai-cung-tai-bach-nid-1246.html",
    "https://tuvi.cohoc.net/luan-giai-cung-tu-tuc-nid-1247.html",
    "https://tuvi.cohoc.net/luan-giai-cung-phu-the-nid-1248.html",
    "https://tuvi.cohoc.net/luan-giai-cung-huynh-de-nid-1249.html",

    # ===== 14 CHÍNH TINH =====
    "https://tuvi.cohoc.net/sao-tu-vi-tinh-bi-cap-luan-giai-sao-tu-vi-nid-4570.html",
    "https://tuvi.cohoc.net/sao-thien-co-nid-3732.html",
    "https://tuvi.cohoc.net/sao-thai-duong-nid-4975.html",
    "https://tuvi.cohoc.net/sao-vu-khuc-nid-183.html",
    "https://tuvi.cohoc.net/sao-thien-dong-nid-887.html",
    "https://tuvi.cohoc.net/sao-liem-trinh-nid-191.html",
    "https://tuvi.cohoc.net/sao-thien-phu-nid-19485.html",
    "https://tuvi.cohoc.net/sao-thai-am-nid-3731.html",
    "https://tuvi.cohoc.net/sao-tham-lang-nid-890.html",
    "https://tuvi.cohoc.net/sao-cu-mon-nid-24233.html",
    "https://tuvi.cohoc.net/sao-thien-tuong-nid-184.html",
    "https://tuvi.cohoc.net/sao-thien-luong-nid-186.html",
    "https://tuvi.cohoc.net/sao-that-sat-nid-4962.html",
    "https://tuvi.cohoc.net/pha-quan-nid-1703.html",
]


def print_banner():
    print("\n" + "=" * 70)
    print("  🚀 CRAWL TUVICOCHOC.NET — Auto Retry + Skip Duplicates")
    print("=" * 70)
    print(f"  ⏰ Bắt đầu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📋 Tổng URLs: {len(URLS_TO_CRAWL)}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_banner()

    # Khởi tạo crawler
    crawler = TuViCrawler(respect_robots=True, delay=2.5)

    # Kiểm tra robots
    if not crawler.can_fetch("https://tuvi.cohoc.net/"):
        print("⛔ Robots.txt không cho phép crawl")
        response = input("   Vẫn tiếp tục? (y/N): ")
        if response.lower() != "y":
            print("   Dừng.")
            raise SystemExit(0)

    # Thống kê state hiện có
    stats = crawler.state.get_stats()
    print(f"📊 State hiện tại:")
    print(f"   ✅ Đã crawl: {stats['completed']} URLs")
    print(f"   ⚠️  Thất bại: {stats['failed']} URLs\n")

    # Chạy crawl
    start_time = time.time()
    try:
        results = crawler.crawl_list(URLS_TO_CRAWL)
    except KeyboardInterrupt:
        print("\n\n⚠️  Người dùng dừng. Đang lưu state...")
        crawler.state.save()
        print("✅ Đã lưu state. Chạy lại script sẽ tiếp tục từ chỗ dừng.")
        raise SystemExit(0)

    elapsed = time.time() - start_time

    # In kết quả
    print()
    crawler.print_stats()
    print()
    print("=" * 70)
    print(f"  ⏱️  Thời gian: {elapsed:.1f}s ({elapsed / 60:.1f} phút)")
    print(f"  ✅ Crawled mới: {len(results)} files")
    print(f"  ⏰ Kết thúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # In danh sách URLs còn lỗi
    failed = crawler.state.state.get("failed", {})
    if failed:
        print(f"\n⚠️  Còn {len(failed)} URLs thất bại:")
        for url, info in list(failed.items())[:5]:
            print(f"   - {url[:70]}")
            print(f"     Lỗi: {info.get('error')} (attempts: {info.get('attempts')})")
        if len(failed) > 5:
            print(f"   ... và {len(failed) - 5} URLs khác")
        print(f"\n   💡 Chạy lại script để retry — nó sẽ tự động skip URLs đã thành công.")