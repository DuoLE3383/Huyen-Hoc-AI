"""Sinh diễn giải 64 quẻ Kinh Dịch bằng Ollama. Chạy 1 lần, cache JSON."""
import json, time, sys
from pathlib import Path
import httpx

OLLAMA = "http://172.31.144.1:11434"
MODEL = "qwen2.5:3b"                        # đổi thành qwen2.5:3b nếu muốn nhanh
OUT_DIR = Path(__file__).parent.parent / "data" / "knowledge" / "kinh_dich"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 64 quẻ — copy từ divination/kinh_dich.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from divination.kinh_dich import HEXAGRAM_NAMES, HEXAGRAM_THEMES

PROMPT = """Bạn là chuyên gia Kinh Dịch. Viết diễn giải cho **Quẻ {num} - {name}** ({theme}).

Yêu cầu (tiếng Việt, ngắn gọn, súc tích, dùng gạch đầu dòng):

1. **Ý nghĩa quẻ** (3-4 câu): Tượng quẻ, thông điệp cốt lõi, cát/hung.
2. **Lời khuyên chung** (2-3 gạch đầu dòng): Nên/không nên làm gì.
3. **Ứng dụng theo lĩnh vực** (mỗi lĩnh vực 1-2 câu):
   - 💕 Tình duyên
   - 💼 Sự nghiệp
   - 🌿 Sức khỏe
   - 💰 Tài vận
   - 🎓 Học hành

Không dùng markdown headings (##), chỉ dùng **bold** và gạch đầu dòng. Không giải thích dài dòng."""

def gen_one(num: int, name: str, theme: str) -> dict:
    prompt = PROMPT.format(num=num, name=name, theme=theme)
    r = httpx.post(
        f"{OLLAMA}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=180.0,
    )
    r.raise_for_status()
    return {
        "que_so": num,
        "ten_que": name,
        "theme": theme,
        "dien_giai": r.json().get("response", "").strip(),
        "model": MODEL,
    }

def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 64

    for i in range(start, end + 1):
        name = HEXAGRAM_NAMES[i-1]
        theme = HEXAGRAM_THEMES[i-1]
        out_file = OUT_DIR / f"que-{i:02d}.json"

        if out_file.exists():
            print(f"· skip {i:02d} {name}")
            continue

        t0 = time.time()
        try:
            data = gen_one(i, name, theme)
            out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✅ {i:02d} {name} ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"❌ {i:02d} {name}: {e}")

if __name__ == "__main__":
    main()
