"""
Crawl 64 quẻ Kinh Dịch từ hocvienlyso.org (Nguyễn Hiến Lê + bổ sung).
Output: backend/data/knowledge/kinh_dich/hocvienlyso/que-NN.json
"""
from __future__ import annotations

import asyncio
import json
import re
import unicodedata
import unicodedata
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE = "https://hocvienlyso.org"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge" / "kinh_dich" / "hocvienlyso"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


# ═══ URL pattern: /que-NN-slug.html ═══
# Ví dụ: /que-22-son-hoa-bi.html
QUE_URLS = {
    1: "que-1-thuan-can", 2: "que-2-thuan-khon", 3: "que-3-thuy-loi-truan",
    4: "que-4-son-thuy-mong", 5: "que-5-thuy-thien-nhu", 6: "que-6-thien-thuy-tung",
    7: "que-7-dia-thuy-su", 8: "que-8-thuy-dia-ty", 9: "que-9-phong-thien-tieu-suc",
    10: "que-10-thien-trach-ly", 11: "que-11-dia-thien-thai", 12: "que-12-thien-dia-bi",
    13: "que-13-thien-hoa-dong-nhan", 14: "que-14-hoa-thien-dai-huu",
    15: "que-15-dia-son-khiem", 16: "que-16-loi-dia-du", 17: "que-17-trach-loi-tuy",
    18: "que-18-son-phong-co", 19: "que-19-dia-trach-lam", 20: "que-20-phong-dia-quan",
    21: "que-21-hoa-loi-phe-hap", 22: "que-22-son-hoa-bi", 23: "que-23-son-dia-bac",
    24: "que-24-dia-loi-phuc", 25: "que-25-thien-loi-vo-vong",
    26: "que-26-son-thien-dai-suc", 27: "que-27-son-loi-di", 28: "que-28-trach-phong-dai-qua",
    29: "que-29-thuan-kham", 30: "que-30-thuan-ly", 31: "que-31-trach-son-ham",
    32: "que-32-loi-phong-hang", 33: "que-33-thien-son-don", 34: "que-34-loi-thien-dai-trang",
    35: "que-35-hoa-dia-tan", 36: "que-36-dia-hoa-minh-di", 37: "que-37-phong-hoa-gia-nhan",
    38: "que-38-hoa-trach-khue", 39: "que-39-thuy-son-kien", 40: "que-40-loi-thuy-giai",
    41: "que-41-son-trach-ton", 42: "que-42-phong-loi-ich", 43: "que-43-trach-thien-quai",
    44: "que-44-thien-phong-cau", 45: "que-45-trach-dia-tuy", 46: "que-46-dia-phong-thang",
    47: "que-47-trach-thuy-khon", 48: "que-48-thuy-phong-tinh", 49: "que-49-trach-hoa-cach",
    50: "que-50-hoa-phong-dinh", 51: "que-51-thuan-chan", 52: "que-52-thuan-can",
    53: "que-53-phong-son-tiem", 54: "que-54-loi-trach-quy-muoi",
    55: "que-55-loi-hoa-phong", 56: "que-56-hoa-son-lu", 57: "que-57-thuan-ton",
    58: "que-58-thuan-doai", 59: "que-59-phong-thuy-hoan", 60: "que-60-thuy-trach-tiet",
    61: "que-61-phong-trach-trung-phu", 62: "que-62-loi-son-tieu-qua",
    63: "que-63-thuy-hoa-ky-te", 64: "que-64-hoa-thuy-vi-te",
}




def _nfc(txt: str) -> str:
    """Normalize Unicode về NFC (gộp dấu)."""
    return unicodedata.normalize("NFC", txt or "")



def _nfc(txt: str) -> str:
    """Normalize Unicode về NFC (gộp dấu)."""
    return unicodedata.normalize("NFC", txt or "")

def parse_que(html: str, que_so: int) -> dict:
    """Parse HTML 1 quẻ — hỗ trợ 3 format khác nhau."""
    soup = BeautifulSoup(html, "html.parser")

    content = (
        soup.find("div", class_="jeg_main_content")
        or soup.find("div", class_="entry-content")
        or soup.find("article")
        or soup
    )

    paragraphs = [_nfc(p.get_text(" ", strip=True)) for p in content.find_all("p")]

    result = {
        "que_so": que_so,
        "title": "",
        "ten_han": "",
        "ten_viet": "",
        "thoan_tu": {"han": "", "han_viet": "", "dich": "", "giang": ""},
        "hao_tu": [],
        "dai_y": "",
    }

    h1 = soup.find("h1", class_="jeg_post_title") or soup.find("h1")
    if h1:
        result["title"] = _nfc(h1.get_text(strip=True))

    # ═══ BƯỚC 1: Tìm tất cả Hán tự + Hán-Việt ═══
    # Pattern Hán: 1-3 ký tự Hán + ":" + Hán tự
    han_pattern = re.compile(r"^([\u4e00-\u9fff]{1,3})[：:]\s*([\u4e00-\u9fff].+)$")
    # Pattern hào có số: "1. 初九: ..."
    hao_num_pattern = re.compile(r"^(\d+)\.?\s*([\u4e00-\u9fff]{1,3})[：:]\s*([\u4e00-\u9fff].+)$")
    # Pattern Hán-Việt (thoán): TỔNG QUÁT — BẤT KỲ chữ cái + ":" + nội dung
    # Ví dụ: "Bí: hanh", "Khốn: Hanh", "Cấn: Cấn kì chỉ..."
    hv_thoan_pattern = re.compile(r"^([A-ZĐ][\w\u00C0-\u024F\u1EA0-\u1EFF]{0,15})[：:]\s*([A-Za-z\u00C0-\u024F\u1EA0-\u1EFF].+)$")
    # Pattern Hán-Việt hào: TỔNG QUÁT
    # Ví dụ: "Sơ lục: Đồn khốn...", "Cửu nhị: Khốn vu tửu...", "Lục tam: ..."
    hv_hao_pattern = re.compile(
        r"^(Sơ|Cửu|Lục|Thượng|Dụng)[\s]+(nhị|tam|tứ|ngũ|lục|cửu|[nhịtamứ ngũlục cửu]+)[\s]*[：:](.+)$",
        re.IGNORECASE
    )

    current_hao = None
    in_hao_section = False

    for i, p in enumerate(paragraphs):
        # Phát hiện bắt đầu section Hào từ
        if re.match(r"^Hào từ[:：]?", p) or p.startswith("Từ đây trở xuống"):
            in_hao_section = True
            continue

        # Nếu chưa vào hào section → parse thoán
        if not in_hao_section:
            m_hao_num = hao_num_pattern.match(p)
            if m_hao_num:
                # Hào có số — chuyển sang hào section ngay
                in_hao_section = True
                if current_hao:
                    result["hao_tu"].append(current_hao)
                current_hao = {
                    "so": int(m_hao_num.group(1)),
                    "ten_han": m_hao_num.group(2),
                    "han": m_hao_num.group(3).strip(),
                    "han_viet": "",
                    "dich": "",
                    "giang": "",
                }
                continue

            # Thoán từ Hán
            m_han = han_pattern.match(p)
            if m_han and not result["thoan_tu"]["han"]:
                result["thoan_tu"]["han"] = p
                continue

            # Thoán từ Hán-Việt — match rộng: bắt đầu bằng CHỮ HOA + ":" + nội dung
            m_hv = re.match(r"^([A-ZĐ][\w\u00C0-\u024F\u1EA0-\u1EFF]{0,20})[：:]\s*(.+)$", p)
            if m_hv and m_hv.group(1).lower() not in ("dịch", "giảng", "giảng.", "dịch."):
                # Ghép dòng tiếp theo nếu bị ngắt
                hv_text = p
                j = i + 1
                while j < len(paragraphs):
                    nxt = paragraphs[j]
                    nxt_lc = nxt.lower().strip()
                    # DỪNG NGAY khi gặp marker
                    if (not nxt
                        or nxt_lc.startswith("dịch")
                        or nxt_lc.startswith("giảng")
                        or nxt_lc.startswith("thoán truyện")
                        or nxt_lc.startswith("đại tượng")
                        or nxt_lc.startswith("hào từ")
                        or re.match(r"^\d+\.", nxt)
                        or re.match(r"^[\u4e00-\u9fff]", nxt)
                        or len(nxt) > 300):
                        break
                    # Chỉ ghép nếu bắt đầu bằng CHỮ HOA
                    if re.match(r"^[A-ZĐ]", nxt):
                        hv_text += " " + nxt
                        j += 1
                    else:
                        break
                if not result["thoan_tu"]["han_viet"]:
                    result["thoan_tu"]["han_viet"] = hv_text
                continue

            # Dịch/Giảng của thoán (case-insensitive)
            p_lc = p.lower().strip()
            if p_lc.startswith("dịch:") and not result["thoan_tu"]["dich"]:
                result["thoan_tu"]["dich"] = p[p.find(":")+1:].strip()
            elif p_lc.startswith("giảng:") and not result["thoan_tu"]["giang"]:
                result["thoan_tu"]["giang"] = p[p.find(":")+1:].strip()

        else:
            # Đang trong hào section
            # Phát hiện hào mới có số: "2. 六二: ..."
            m_hao_num = hao_num_pattern.match(p)
            if m_hao_num:
                if current_hao:
                    result["hao_tu"].append(current_hao)
                current_hao = {
                    "so": int(m_hao_num.group(1)),
                    "ten_han": m_hao_num.group(2),
                    "han": m_hao_num.group(3).strip(),
                    "han_viet": "",
                    "dich": "",
                    "giang": "",
                }
                continue

            # Hào không có số — "初 九: 潛 龍 勿 用" (có dấu cách)
            m_han_nospace = re.match(r"^([\u4e00-\u9fff])\s*([\u4e00-\u9fff])[：:]\s*(.+)$", p)
            if m_han_nospace and not current_hao:
                # Hào đầu tiên không có số
                current_hao = {
                    "so": 1,
                    "ten_han": m_han_nospace.group(1) + m_han_nospace.group(2),
                    "han": m_han_nospace.group(3).strip(),
                    "han_viet": "",
                    "dich": "",
                    "giang": "",
                }
                continue

            if current_hao:
                p_lc = p.lower().strip()
                # Hán-Việt hào — bắt đầu bằng Sơ/Cửu/Lục/Thượng/Dụng
                m_hv_hao = re.match(
                    r"^(Sơ|Cửu|Lục|Thượng|Dụng)\s+[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+\s*[：:](.+)$",
                    p, re.IGNORECASE
                )
                if m_hv_hao and not current_hao["han_viet"]:
                    current_hao["han_viet"] = p
                elif p_lc.startswith("dịch:") and not current_hao["dich"]:
                    current_hao["dich"] = p[p.find(":")+1:].strip()
                elif p_lc.startswith("giảng:") and not current_hao["giang"]:
                    current_hao["giang"] = p[p.find(":")+1:].strip()

    if current_hao:
        result["hao_tu"].append(current_hao)

    # Sắp xếp hào theo số
    result["hao_tu"].sort(key=lambda x: x["so"])

    # Trích tên Hán + Việt
    for p in paragraphs[:8]:
        m = re.search(r"\(([\u4e00-\u9fff]+)\s+([a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ0-9]+)\)", p)
        if m:
            result["ten_han"] = m.group(1)
            result["ten_viet"] = m.group(2)
            break

    # Đại ý (cuối bài)
    for p in reversed(paragraphs):
        if "Đại ý" in p or "Tóm lại" in p:
            result["dai_y"] = p
            break

    return result



async def fetch_que(client: httpx.AsyncClient, que_so: int, slug: str) -> dict | None:
    url = f"{BASE}/{slug}.html"
    try:
        r = await client.get(url, headers=HEADERS, timeout=30.0)
        r.raise_for_status()
        data = parse_que(r.text, que_so)
        n_hao = len(data["hao_tu"])
        has_thoan = bool(data["thoan_tu"]["han"] and data["thoan_tu"]["han_viet"])
        print(f"  Quẻ {que_so:>2} — {n_hao} hào, thoán={'✓' if has_thoan else '✗'}")
        return data
    except Exception as e:
        print(f"  Quẻ {que_so:>2} — LỖI: {e}")
        return None


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(follow_redirects=True, max_redirects=5) as client:
        for que_so in sorted(QUE_URLS):
            out = OUT_DIR / f"que-{que_so:02d}.json"
            if out.exists() and out.stat().st_size > 500:
                print(f"  Quẻ {que_so:>2} — skip (đã có)")
                continue

            data = await fetch_que(client, que_so, QUE_URLS[que_so])
            if data:
                out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            await asyncio.sleep(1.5)

    print(f"\n✅ Output: {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
