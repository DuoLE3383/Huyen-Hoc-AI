"""Secure coin-cast I Ching draws and King Wen hexagram lookup."""
from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any

from services.ollama_client import ollama
from knowledge.kinh_dich_rag import get_context
from services.ollama_client import build_time_context
from knowledge import kinh_dich_cache as _cache


TRIGRAMS = {
    (1, 1, 1): ("Càn", "☰", "Trời"),
    (1, 1, 0): ("Đoài", "☱", "Đầm"),
    (1, 0, 1): ("Ly", "☲", "Lửa"),
    (1, 0, 0): ("Chấn", "☳", "Sấm"),
    (0, 1, 1): ("Tốn", "☴", "Gió"),
    (0, 1, 0): ("Khảm", "☵", "Nước"),
    (0, 0, 1): ("Cấn", "☶", "Núi"),
    (0, 0, 0): ("Khôn", "☷", "Đất"),
}
TRIGRAM_ORDER = ["Càn", "Đoài", "Ly", "Chấn", "Tốn", "Khảm", "Cấn", "Khôn"]

KING_WEN = [
    [1, 10, 13, 25, 44, 6, 33, 12],
    [43, 58, 49, 17, 28, 47, 31, 45],
    [14, 38, 30, 21, 50, 64, 56, 35],
    [34, 54, 55, 51, 32, 40, 62, 16],
    [9, 61, 37, 42, 57, 59, 53, 20],
    [5, 60, 63, 3, 48, 29, 39, 8],
    [26, 41, 22, 27, 18, 4, 52, 23],
    [11, 19, 36, 24, 46, 7, 15, 2],
]
HEXAGRAM_NAMES = [
    "Thuần Càn", "Thuần Khôn", "Thủy Lôi Truân", "Sơn Thủy Mông",
    "Thủy Thiên Nhu", "Thiên Thủy Tụng", "Địa Thủy Sư", "Thủy Địa Tỷ",
    "Phong Thiên Tiểu Súc", "Thiên Trạch Lý", "Địa Thiên Thái", "Thiên Địa Bĩ",
    "Thiên Hỏa Đồng Nhân", "Hỏa Thiên Đại Hữu", "Địa Sơn Khiêm", "Lôi Địa Dự",
    "Trạch Lôi Tùy", "Sơn Phong Cổ", "Địa Trạch Lâm", "Phong Địa Quán",
    "Hỏa Lôi Phệ Hạp", "Sơn Hỏa Bí", "Sơn Địa Bác", "Địa Lôi Phục",
    "Thiên Lôi Vô Vọng", "Sơn Thiên Đại Súc", "Sơn Lôi Di", "Trạch Phong Đại Quá",
    "Thuần Khảm", "Thuần Ly", "Trạch Sơn Hàm", "Lôi Phong Hằng",
    "Thiên Sơn Độn", "Lôi Thiên Đại Tráng", "Hỏa Địa Tấn", "Địa Hỏa Minh Di",
    "Phong Hỏa Gia Nhân", "Hỏa Trạch Khuê", "Thủy Sơn Kiển", "Lôi Thủy Giải",
    "Sơn Trạch Tổn", "Phong Lôi Ích", "Trạch Thiên Quải", "Thiên Phong Cấu",
    "Trạch Địa Tụy", "Địa Phong Thăng", "Trạch Thủy Khốn", "Thủy Phong Tỉnh",
    "Trạch Hỏa Cách", "Hỏa Phong Đỉnh", "Thuần Chấn", "Thuần Cấn",
    "Phong Sơn Tiệm", "Lôi Trạch Quy Muội", "Lôi Hỏa Phong", "Hỏa Sơn Lữ",
    "Thuần Tốn", "Thuần Đoài", "Phong Thủy Hoán", "Thủy Trạch Tiết",
    "Phong Trạch Trung Phu", "Lôi Sơn Tiểu Quá", "Thủy Hỏa Ký Tế", "Hỏa Thủy Vị Tế",
]
HEXAGRAM_THEMES = [
    "Chủ động và chính trực", "Nuôi dưỡng và tiếp nhận", "Khởi đầu giữa thử thách",
    "Học hỏi trước điều chưa biết", "Kiên nhẫn chờ thời", "Đối thoại và xử lý bất đồng",
    "Kỷ luật và cùng phối hợp", "Tìm sự đồng lòng", "Tiến từng bước nhỏ",
    "Giữ chừng mực khi tiến lên", "Hài hòa và hanh thông", "Nhận biết giai đoạn trì trệ",
    "Hợp tác vì mục tiêu chung", "Quản lý thành quả có trách nhiệm",
    "Khiêm nhường và cân bằng", "Chuẩn bị cho cơ hội", "Linh hoạt trước thay đổi",
    "Sửa điều cũ để làm mới", "Tiến gần với sự quan tâm", "Quan sát trước khi quyết định",
    "Nhìn thẳng vào hệ quả", "Chú trọng nền tảng và hình thức",
    "Buông bỏ điều không còn phù hợp", "Trở về với gốc rễ",
    "Hành động chân thành, không cưỡng cầu", "Tích lũy và chuẩn bị",
    "Nuôi dưỡng thân tâm đúng cách", "Chấp nhận gánh nặng lớn",
    "Vượt qua hiểm nguy bằng bình tĩnh", "Giữ sáng suốt và chính trực",
    "Cảm ứng và kết nối", "Bền vững qua thời gian",
    "Rút lui đúng lúc", "Dùng sức mạnh đúng chỗ", "Tiến lên không ngừng",
    "Giữ ánh sáng giữa nghịch cảnh", "Xây dựng gia đình và tổ chức",
    "Tôn trọng khác biệt", "Tìm lối đi thận trọng qua trở ngại",
    "Giải tỏa nút thắt", "Giảm bớt để tăng thêm", "Tăng trưởng có kiểm soát",
    "Quyết đoán loại bỏ điều xấu", "Gặp gỡ đúng người đúng lúc",
    "Tập hợp và kết nối", "Vươn lên không ngừng", "Vượt khốn bằng nội lực",
    "Bảo dưỡng nguồn lực chung", "Thay cũ đổi mới", "Định vị và nuôi dưỡng",
    "Chấn động để tỉnh thức", "Dừng lại đúng lúc", "Tiến từng bước vững chắc",
    "Tôn trọng cam kết và cảm xúc", "Tỏa sáng rực rỡ", "Đi xa cần giữ mình",
    "Thuận theo và thấm sâu", "Vui vẻ và giao hòa", "Tan rã để tái tạo",
    "Tiết chế và giới hạn", "Chân thành từ bên trong", "Vượt quá nhỏ bé",
    "Hoàn thành chu kỳ", "Chưa hoàn thành, tiếp tục",
]


def _normalize_hao(values: list[int]) -> list[dict[str, Any]]:
    return [{"vi_tri": i + 1, "duong": bool(v), "dong": False} for i, v in enumerate(values)]


def _king_wen_index(values: list[int]) -> int:
    lower = tuple(values[:3])
    upper = tuple(values[3:])
    lower_idx = TRIGRAM_ORDER.index(TRIGRAMS[lower][0])
    upper_idx = TRIGRAM_ORDER.index(TRIGRAMS[upper][0])
    return KING_WEN[upper_idx][lower_idx]


def _hexagram(values: list[int]) -> dict[str, Any]:
    so = _king_wen_index(values)
    lower = tuple(values[:3])
    upper = tuple(values[3:])
    return {
        "so": so,
        "ten": HEXAGRAM_NAMES[so - 1],
        "chu_de": HEXAGRAM_THEMES[so - 1],
        "thuong_quai": {"ten": TRIGRAMS[upper][0], "tuong": TRIGRAMS[upper][1]},
        "ha_quai": {"ten": TRIGRAMS[lower][0], "tuong": TRIGRAMS[lower][1]},
        "hao": _normalize_hao(values),
    }


def gieo_que() -> dict[str, Any]:
    """
    Gieo 6 hào bằng 3 đồng xu — MỘT LẦN DUY NHẤT, nhất quán 100%.

    Mỗi hào:
      - 6 (2+2+2) = Lão Âm      -> âm,  động, biến thành dương
      - 7 (2+2+3) = Thiếu Dương -> dương, tĩnh
      - 8 (2+3+3) = Thiếu Âm    -> âm,  tĩnh
      - 9 (3+3+3) = Lão Dương   -> dương, động, biến thành âm

    Trả về:
      que_chinh, que_bien, hao_dong (list vị trí 1..6),
      coins_log (để client animate đồng xu khớp data)
    """
    hao_chinh: list[int] = []   # 0 = âm, 1 = dương
    hao_bien:  list[int] = []
    hao_dong:  list[int] = []
    coins_log: list[dict[str, Any]] = []

    for i in range(6):
        coins = [secrets.randbelow(2) for _ in range(3)]  # 0 = ngửa, 1 = sấp
        tong = sum(3 if c else 2 for c in coins)

        if tong == 6:       # Lão Âm
            hao_chinh.append(0); hao_bien.append(1); hao_dong.append(i + 1)
        elif tong == 7:     # Thiếu Dương
            hao_chinh.append(1); hao_bien.append(1)
        elif tong == 8:     # Thiếu Âm
            hao_chinh.append(0); hao_bien.append(0)
        else:               # tong == 9, Lão Dương
            hao_chinh.append(1); hao_bien.append(0); hao_dong.append(i + 1)

        coins_log.append({"coins": coins, "tong": tong})

    que_chinh = _hexagram(hao_chinh)
    for h in que_chinh["hao"]:
        h["dong"] = h["vi_tri"] in hao_dong

    que_bien = None
    if hao_dong:
        que_bien = _hexagram(hao_bien)
        for h in que_bien["hao"]:
            h["dong"] = h["vi_tri"] in hao_dong

    return {
        "que_chinh": que_chinh,
        "que_bien": que_bien,
        "hao_dong": hao_dong,
        "coins_log": coins_log,
    }


def validate_question(question: str) -> str:
    q = (question or "").strip()
    if len(q) < 5:
        raise ValueError("Câu hỏi cần ít nhất 5 ký tự.")
    if len(q) > 500:
        raise ValueError("Câu hỏi không quá 500 ký tự.")
    return q


LANG_GUARD = (
    "BẮT BUỘC trả lời 100% bằng tiếng Việt. "
    "TUYỆT ĐỐI KHÔNG dùng tiếng Trung, tiếng Anh, ký tự Hán, hoặc trộn ngôn ngữ. "
    "Nếu cần từ chuyên môn, dùng từ Hán-Việt hoặc từ gốc."
)


# ═══ Nguyên tắc luận giải Kinh Dịch (áp dụng cho mọi prompt) ═══
NGUYEN_TAC_LUAN_GIAI = '''
NGUYÊN TẮC LUẬN GIẢI KINH DỊCH (BẮT BUỘC):

1. LUẬN QUẺ TRƯỚC, KẾT LUẬN SAU.
   Trình tự: hiểu câu hỏi -> đọc quẻ chủ -> phân tích hào động -> đọc quẻ biến -> tổng hợp -> kết luận -> lời khuyên.

2. MỌI KẾT LUẬN PHẢI CÓ CĂN CỨ.
   Phải chỉ rõ: tên quẻ, tượng quái, hào động, ngũ hành sinh/khắc với nhật chủ. KHÔNG BỊA hào, can chi, nguồn.

3. ĐỊNH DẠNG OUTPUT ĐÚNG SCHEMA.
   Trường "N câu" = 1 STRING. Trường "bullet points" = array[string].

4. HÀO ĐỘNG — BẮT BUỘC.
   Nếu đầu "Thông tin quẻ" có "HÀO ĐỘNG: [X, Y]" -> PHẢI viết 3-5 câu phân tích hào X, Y trong `luan_giai_hao_dong`.
   TUYỆT ĐỐI KHÔNG viết "Không có hào động" khi có hào. CHỈ phân tích hào được liệt kê.

5. TÊN HÀO CHUẨN — 6 dạng duy nhất:
   Hào 1: Sơ Lục/Cửu | Hào 2: Lục/Cửu Nhị | Hào 3: Lục/Cửu Tam
   Hào 4: Lục/Cửu Tứ | Hào 5: Lục/Cửu Ngũ | Hào 6: Thượng Lục/Cửu
   KHÔNG dùng "Thất Lục", "Bát Lục".

6. DỤNG THẦN — theo bảng đã cho, KHÔNG bịa.
'''

SYSTEM_JSON = "Bạn là chuyên gia Kinh Dịch. Chỉ trả về JSON object hợp lệ, không markdown, không giải thích."

def _build_que_info(result: dict[str, Any]) -> str:
    qc = result["que_chinh"]
    qb = result.get("que_bien")
    hao_dong = [h["vi_tri"] for h in qc.get("hao", []) if h.get("dong")]

    hao_line = f"HÀO ĐỘNG: {hao_dong}" if hao_dong else "HÀO ĐỘNG: không có (quẻ tĩnh)"
    lines = [
        hao_line,
        f"Quẻ chính {qc['so']} — {qc['ten']} (chủ đề: {qc['chu_de']})",
        f"  Thượng {qc['thuong_quai']['ten']} / Hạ {qc['ha_quai']['ten']}",
    ]
    if qb:
        lines.append(f"Quẻ biến {qb['so']} — {qb['ten']} (chủ đề: {qb['chu_de']})")
    else:
        lines.append("Quẻ biến: không có")
    return "\n".join(lines)


async def _prompt_1_core(question: str, que_info: str, context: str) -> str:
    time_ctx = build_time_context()

    # Tính 7 ngày tới để LLM có dữ liệu cụ thể
    from datetime import datetime, timedelta
    today = datetime.now()
    days_str_short = "\n".join([
        f"- {(today + timedelta(days=i)).strftime('%d/%m/%Y (%A)')}"
        for i in range(0, 4)
    ])

    # ═══ TRÍCH XUẤT HÀO ĐỘNG — ĐƯA LÊN ĐẦU PROMPT ═══
    import re as _re
    _m = _re.search(r'HÀO ĐỘNG:\s*\[([^\]]*)\]', que_info)
    if _m:
        _v = _m.group(1).strip()
        if _v:
            hao_dong_top = (
                f"\n## ⚡⚡⚡ HÀO ĐỘNG: [{_v}] ⚡⚡⚡\n"
                f"## -> BẮT BUỘC phân tích các hào {_v} trong field `luan_giai_hao_dong`.\n"
                f"## -> TUYỆT ĐỐI KHÔNG viết 'Không có hào động' khi có hào ở đây.\n"
            )
        else:
            hao_dong_top = "\n## ⚡ HÀO ĐỘNG: KHÔNG CÓ (quẻ tĩnh).\n"
    else:
        hao_dong_top = ""

    prompt = f"""{LANG_GUARD}
{hao_dong_top}

{time_ctx}

## 3 NGÀY TỚI (dùng ĐÚNG, KHÔNG bịa):
{days_str_short}

Ngũ hành: Mộc→Hỏa→Thổ→Kim→Thủy→Mộc (sinh); Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, Hỏa khắc Kim, Kim khắc Mộc.

Bạn là học giả Kinh Dịch Nho gia Việt Nam. Dùng TƯ LIỆU bên dưới, KHÔNG bịa.

## Câu hỏi người dùng:
{question}

## Thông tin quẻ:
{que_info}

## TƯ LIỆU (Hán-Việt + Dịch + Giảng — CHỈ DÙNG ĐÚNG cái này, KHÔNG bịa):
{context}

## QUY TẮC:
- Dùng ĐÚNG tên quẻ, số quẻ, hào động trong "Thông tin quẻ". KHÔNG bịa Hán tự.
- **ket_luan**: CHỈ 1 trong 3 — `"CÁT"` | `"HUNG"` | `"TĨNH"`. CÁT=quẻ tốt+ngũ hành sinh trợ+hào thuận. HUNG=quẻ xấu/khắc/hào xấu. TĨNH=trung tính/chờ thời.
- **thoi_diem_tot_nhat** / **thoi_diem_nen_tranh**: CHỈ 1 ngày mỗi field, dùng đúng danh sách 3 ngày trên.

## Cấu trúc JSON trả về:

{{
  "thoan_tu": {{"han_viet": "...", "dich": "...", "giang": "..."}},
  "tuong_tu": {{"dich": "...", "bai_hoc": "..."}},
  "ket_luan": "CÁT",
  "ket_luan_y_nghia": "...",
  "ly_do": "...",
  "thoi_diem_tot_nhat": "...",
  "thoi_diem_nen_tranh": "...",
  "loi_khuyen": "...",
  "tom_tat": "...",
  "do_tin_cay": "...",
  "dieu_kien_hanh_dong": ["...", "..."],
  "canh_bao": ["...", "..."]
}}"""
    return prompt


async def _prompt_2_tam_hop(
    question: str,
    que_info: str,
    cast: dict[str, Any] | None = None,
    bat_tu: dict[str, Any] | None = None,
) -> str:
    # ═══ Tính Nạp Giáp chính xác nếu có cast + bát tự ═══
    nap_giap_ctx = ""
    if cast and bat_tu:
        try:
            from bat_tu.nap_giap import format_nap_giap_cho_prompt
            nhat_chu_hanh = bat_tu.get("nhat_chu_hanh", "")
            if nhat_chu_hanh:
                nap_giap_ctx = format_nap_giap_cho_prompt(cast["que_chinh"], nhat_chu_hanh)
        except Exception:
            pass

    prompt = f"""{LANG_GUARD}

{NGUYEN_TAC_LUAN_GIAI}

## ⛔ QUY LUẬT NGŨ HÀNH — KHÔNG ĐƯỢC SAI:
- **Tương sinh**: Mộc -> Hỏa -> Thổ -> Kim -> Thủy -> Mộc
  (Nghĩa là: Mộc sinh Hỏa, Hỏa sinh Thổ, **Thổ sinh Kim**, Kim sinh Thủy, Thủy sinh Mộc)
- **Tương khắc**: Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, **Hỏa khắc Kim**, Kim khắc Mộc

**Ví dụ đúng**:
- Hào Thổ + Nhật chủ Kim -> **Thổ SINH Kim** (không phải khắc)
- Hào Hỏa + Nhật chủ Kim -> **Hỏa KHẮC Kim**
- Hào Kim + Nhật chủ Kim -> **tỷ hòa**

**Nếu viết sai quy luật -> kết quả vô giá trị.**

---

Bạn là chuyên gia Kinh Dịch. Luận giải "Hào Chuyển" — CHỈ các hào động.

## Câu hỏi: {question}
## Thông tin quẻ: {que_info}

## Nạp Giáp (DỮ LIỆU CHÍNH XÁC — KHÔNG được bịa):
{nap_giap_ctx if nap_giap_ctx else "(Không có — chỉ luận theo tên hào và ý nghĩa)"}

## QUY TẮC BẮT BUỘC:
1. **Tên hào CHỈ 1 trong 12 giá trị:** Sơ Cửu, Sơ Lục, Cửu Nhị, Lục Nhị, Cửu Tam, Lục Tam, Cửu Tứ, Lục Tứ, Cửu Ngũ, Lục Ngũ, Thượng Cửu, Thượng Lục. VD hào 1 âm → "Sơ Lục", hào 1 dương → "Sơ Cửu". KHÔNG dùng tên quái (Thượng Ly, Hạ Tốn...).
2. Nếu bảng Nạp Giáp có can+chi → dùng CHÍNH XÁC. Nếu KHÔNG có → `ung_bat_tu` chỉ nêu quan hệ ngũ hành hào với nhật chủ (sinh/khắc/tỷ hòa), KHÔNG bịa can chi.
3. Phân tích ngũ hành theo: Sinh Mộc→Hỏa→Thổ→Kim→Thủy→Mộc; Khắc Kim khắc Mộc, Mộc khắc Thổ, Thổ khắc Thủy, Thủy khắc Hỏa, Hỏa khắc Kim.
4. **`giang`**: 2-3 câu viết THẬT, không lặp tên hào. Không copy mô tả schema.
5. **`khai_niem`**: 1-2 câu BÁM SÁT quẻ cụ thể + câu hỏi user (nêu hào nào động, chuyển hóa thế nào). KHÔNG viết câu chung chung như "hào động sẽ giúp bạn định hướng".
6. **`tong_hop`**: 3-4 câu cụ thể về tác động của hào động lên câu hỏi user. KHÔNG viết "giúp bạn định hướng" chung chung.

## Cấu trúc:

### 1. Khái niệm hào động
1-2 câu

### 2. Từng hào động (MỖI hào trong "hao_dong"):
- Tên hào + tính chất chuyển hóa
- **Hán** / **Phiên âm** / **Dịch** / **Giảng**
- **Ứng Bát Tự**: can chi hào + sinh khắc với nhật chủ

### 3. Tổng hợp
3-5 câu

Trả về DUY NHẤT JSON. Các field phải có NỘI DUNG THẬT, KHÔNG copy mô tả này vào output:
{{
  "khai_niem": "(viết 1-2 câu thật)",
  "hao_dong": [
    {{"ten": "Sơ Lục", "chuyen_hoa": "Lão Âm → Dương", "han_viet": "(nguyên văn hào từ Hán-Việt, 1 câu)", "giang": "(2-3 câu thật, KHÔNG lặp tên hào)", "ung_bat_tu": "(3-4 câu thật: can+chi + ngũ hành + quan hệ nhật chủ)", "do_tin_cay": "Cao — (1 câu lý do)", "luan_cu": ["căn cứ 1", "căn cứ 2"]}}
  ],
  "tong_hop": "(3-5 câu thật)"
}}"""
    return prompt


async def _prompt_3_action(
    question: str,
    que_info: str,
    bat_tu: dict[str, Any] | None = None,
    ket_luan_crawl: str | None = None,
) -> str:
    bat_tu_ctx = ""
    if bat_tu:
        try:
            from bat_tu.lap_tu_tru import format_bat_tu_context
            bat_tu_ctx = format_bat_tu_context(bat_tu)
        except Exception:
            pass

    # Block kết luận đã crawl — LLM CHỈ diễn giải, KHÔNG tự suy luận
    ket_luan_block = ""
    if ket_luan_crawl:
        ket_luan_block = f"""
## KẾT LUẬN CHUẨN (từ từ điển Kinh Dịch — KHÔNG được bịa khác):
{ket_luan_crawl}

## NHIỆM VỤ:
Diễn giải lại kết luận trên thành văn phong tự nhiên, cá nhân hoá.
GIỮ NGUYÊN ý nghĩa cát/hung, dụng thần, thời điểm.
KHÔNG tự thêm kết luận mới ngoài data trên.
"""

    prompt = f"""{LANG_GUARD}

{NGUYEN_TAC_LUAN_GIAI}

Bạn là chuyên gia Kinh Dịch. Viết "Quẻ Biến" — luận giải xu hướng tương lai.

## Câu hỏi: {question}
## Thông tin quẻ: {que_info}
{bat_tu_ctx}
{ket_luan_block}
## Cấu trúc:

### 1. Xu Hướng Tương Lai
5-7 câu: quẻ biến cho biết tình hình sẽ diễn biến ra sao sau khi hào động hoàn tất

### 2. Lời Khuyên
5-7 câu: nên làm gì để đón xu hướng

### 3. Diệu Nghĩa Cá Nhân (15-38 câu, chia 4 phần rõ ràng)

**(a) Nhật chủ và Quẻ biến** (3-8 câu):
- Nhật chủ mệnh chủ hành gì, vượng/yếu ra sao?
- Quẻ biến hành gì? Sinh/khắc/trợ nhật chủ thế nào?
- Ý nghĩa tương tác này cho câu hỏi cụ thể.

**(b) Hào động chuyển hóa** (3-10 câu):
- Hào động chuyển sang ngũ hành gì?
- Can chi của hào sinh/khắc nhật chủ không?
- Dấu hiệu cát/hung cụ thể.

**(c) Dụng thần và Ứng kỳ** (4-10 câu):
- Dụng thần/Hỷ thần của mệnh chủ là hành gì?
- Quẻ có trợ dụng thần không?
- Thời điểm nào (tháng/quý) thuận lợi? Mùa nào cần tránh?

**(d) Khuyến nghị cá nhân hoá** (5-10 câu):
- Hướng hành động cụ thể (làm gì, ở đâu, với ai)
- Điều cần tránh trong 30 ngày tới
- Lời khuyên cho câu hỏi "{question}" cụ thể.

Trả về DUY NHẤT JSON:
{{
  "xu_huong": "4-10 câu phân tích xu hướng tương lai",
  "loi_khuyen": "TRẢ VỀ 1 CHUỖI STRING DUY NHẤT (KHÔNG PHẢI ARRAY/LIST). 2-3 câu khuyến nghị hành động theo XU HƯỚNG TƯƠNG LAI dựa trên quẻ biến. Nếu quẻ biến thuận -> xác định cơ hội cụ thể và điều kiện để tận dụng. Nếu quẻ biến bất lợi -> chỉ rõ rủi ro và biện pháp giảm thiểu. Nếu quẻ biến trung tính -> nêu điều kiện chuyển sang hành động. Dùng động từ mạnh, câu khẳng định, súc tích. Không dùng 'có thể', 'tùy trường hợp', 'nên cân nhắc'.",
  "do_tin_cay": "Cao | Trung bình | Thấp — kèm 1 câu lý do ngắn về độ chắc chắn của phân tích xu hướng.",
  "dieu_kien_hanh_dong": "3-5 điều kiện thực tế cần kiểm tra trước khi thực hiện hành động đề xuất (bullet points).",
  "canh_bao": "3-5 điểm chưa rõ, giới hạn dữ liệu, hoặc rủi ro khi diễn giải quẻ biến (bullet points).",
  "dieu_nghia_ca_nhan": "12-20 câu chia 4 phần (a)(b)(c)(d), mỗi phần 3-5 câu. PHẢI dài, PHẢI chi tiết, không dưới 500 từ. Đây là phần quan trọng nhất — SẼ BỊ ẨN cho đến khi user xem ads."
}}"""
    return prompt




async def _prompt_3_action_short(
    question: str,
    que_info: str,
) -> str:
    """Prompt NGẮN cho p3 — chỉ xu_huong + loi_khuyen + do_tin_cay.
    Phần dieu_nghia_ca_nhan do _prompt_4_dieu_nghia lo."""
    prompt = f"""{LANG_GUARD}

Bạn là chuyên gia Kinh Dịch. Luận giải QUẺ BIẾN — xu hướng tương lai.

## Câu hỏi: {question}
## Thông tin quẻ:
{que_info}

## Yêu cầu:
- **xu_huong**: 4-6 câu — quẻ biến cho biết tình hình diễn biến ra sao sau hào động. Bám sát ngũ hành + quẻ biến + nhật chủ.
- **loi_khuyen**: 2-3 câu khuyến nghị hành động, dùng động từ mạnh (TIẾN HÀNH / TẠM HOÃN / CHUẨN BỊ / DUY TRÌ).
- **do_tin_cay**: Cao | Trung bình | Thấp + 1 câu lý do.

Trả về DUY NHẤT JSON:
{{
  "xu_huong": "...",
  "loi_khuyen": "...",
  "do_tin_cay": "..."
}}"""
    return prompt


async def _prompt_4_dieu_nghia(
    question: str,
    que_info: str,
    bat_tu: dict[str, Any] | None = None,
) -> str:
    """Prompt riêng cho Diệu Nghĩa Cá Nhân — phần paywall."""
    bat_tu_ctx = ""
    if bat_tu:
        try:
            from bat_tu.lap_tu_tru import format_bat_tu_context
            bat_tu_ctx = format_bat_tu_context(bat_tu)
        except Exception:
            pass

    prompt = f"""{LANG_GUARD}

Viết "Diệu Nghĩa Cá Nhân" — luận giải riêng cho câu hỏi user.

## Câu hỏi: {question}

## QUY TẮC VĂN PHONG:
- **LỜI KHUYÊN PHẢI MẠNH MẼ, DỨT KHOÁT** — dùng động từ mệnh lệnh: **NÊN / PHẢI / ĐỪNG / TRÁNH / HÃY**
- KHÔNG dùng: "có thể", "có lẽ", "tùy trường hợp", "nên cân nhắc", "bạn có thể xem xét"
- Câu khẳng định, câu mệnh lệnh. VD: "PHẢI chờ tới tháng 11 dương lịch" thay vì "có thể chờ"
- Không viết văn hoa, sáo rỗng. Đi thẳng vào hành động cụ thể.

## DỮ LIỆU QUẺ (chỉ đọc khi cần, KHÔNG lặp lại):
{que_info}
{bat_tu_ctx}

## Yêu cầu: Viết 12-20 câu, chia 4 phần rõ ràng:

**(a) Nhật chủ & Quẻ** (3-5 câu):
- Nhật chủ hành gì? Quẻ biến hành gì?
- Sinh/khắc/trợ nhật chủ thế nào?
- Ý nghĩa cho câu hỏi cụ thể.

**(b) Hào động** (3-5 câu):
- Hào động chuyển sang ngũ hành gì?
- Can chi hào sinh/khắc nhật chủ không?
- Dấu hiệu cát/hung cụ thể.

**(c) Dụng thần & Ứng kỳ** (3-5 câu):
- Dụng thần của mệnh chủ là hành gì?
- Quẻ có trợ dụng thần không?
- Thời điểm nào (tháng/quý) thuận lợi?

**(d) Khuyến nghị** (3-5 câu):
- Hướng hành động cụ thể (làm gì, ở đâu, với ai)
- Điều cần tránh trong 30 ngày tới
- Lời khuyên cho câu hỏi "{question}"

Trả về DUY NHẤT JSON. QUAN TRỌNG: `dieu_nghia_ca_nhan` PHẢI là 1 STRING LIỀN MẠCH, KHÔNG phải object/dict, KHÔNG dùng dấu ngoặc nhọn bên trong:
{{
  "dieu_nghia_ca_nhan": "(a) ... (b) ... (c) ... (d) ... — 12-20 câu viết liền mạch, KHÔNG chia nhỏ thành object"
}}"""
    return prompt


def _safe_parse(raw: str) -> dict[str, Any]:
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except (ValueError, TypeError):
        pass
    start, end = raw.find("{"), raw.rfind("}") + 1
    if 0 <= start < end:
        try:
            d = json.loads(raw[start:end])
            return d if isinstance(d, dict) else {}
        except ValueError:
            pass
    return {}


def _strip_chinese(text: str) -> str:
    if not isinstance(text, str):
        return text
    import re
    text = re.sub(r"[\u4e00-\u9fff]+", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _clean_obj(obj: Any, _depth: int = 0) -> Any:
    """Đệ quy xoá ký tự Trung khỏi mọi string trong obj. Max depth 20."""
    if _depth > 20:
        return obj
    if isinstance(obj, str):
        return _strip_chinese(obj)
    if isinstance(obj, list):
        return [_clean_obj(x, _depth + 1) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean_obj(v, _depth + 1) for k, v in obj.items()}
    return obj


async def luan_giai_que(
    question: str,
    cast: dict[str, Any] | None = None,
    bat_tu: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Luận giải Kinh Dịch bằng 3 prompts song song (nhanh + chất lượng cao).

    Args:
        bat_tu: Dict bát tự từ `bat_tu.lap_tu_tru.lap_tu_tru` (BẮT BUỘC khi gọi từ API).
    """
    question = validate_question(question)
    result = cast or gieo_que()
    que_chinh_so = result["que_chinh"]["so"]
    que_bien_so = (result.get("que_bien") or {}).get("so") or que_chinh_so

    # ── Cache check ──
    cached = _cache.get(que_chinh_so, que_bien_so, question)
    if cached is not None:
        return {**result, "cau_hoi": question, "luan_giai": cached}

    context = get_context(que_chinh_so, que_bien_so)
    que_info = _build_que_info(result)

    # Bổ sung bát tự vào que_info nếu có
    if bat_tu:
        try:
            from bat_tu.lap_tu_tru import format_bat_tu_context
            que_info = format_bat_tu_context(bat_tu) + "\n" + que_info
        except Exception:
            pass

    p1 = await _prompt_1_core(question, que_info, context)
    p2 = await _prompt_2_tam_hop(question, que_info, cast=result, bat_tu=bat_tu)
    p3 = await _prompt_3_action(question, que_info)

    r1, r2, r3 = await asyncio.gather(
        ollama.generate(p1, system=SYSTEM_JSON, temperature=0.7, json_mode=True, timeout=180.0, num_predict=1500),
        ollama.generate(p2, system=SYSTEM_JSON, temperature=0.6, json_mode=True, timeout=180.0, num_predict=1500),
        ollama.generate(p3, system=SYSTEM_JSON, temperature=0.7, json_mode=True, timeout=180.0, num_predict=1500),
        return_exceptions=True,
    )

    d1 = _clean_obj(_safe_parse(r1))
    d2 = _clean_obj(_safe_parse(r2))
    d3 = _clean_obj(_safe_parse(r3))

    luan_giai: dict[str, Any] = {}
    luan_giai.update(d1)
    luan_giai.update(d2)
    luan_giai.update(d3)

    _cache.save(que_chinh_so, que_bien_so, question, luan_giai)
    return {**result, "cau_hoi": question, "luan_giai": luan_giai}
