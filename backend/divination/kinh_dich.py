"""Secure coin-cast I Ching draws and King Wen hexagram lookup."""
from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any

from services.ollama_client import ollama
from knowledge.kinh_dich_rag import get_context


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
    """Gieo 6 hào bằng 3 đồng xu (2=âm tĩnh, 3=dương động theo tổng)."""
    hao = []
    for _ in range(6):
        coins = [secrets.randbelow(2) for _ in range(3)]  # 0 = ngửa (âm), 1 = sấp (dương)
        tong = sum(3 if c else 2 for c in coins)
        # 6 = lão âm (động), 7 = thiếu dương, 8 = thiếu âm, 9 = lão dương (động)
        if tong == 6:
            hao.append(0)
        elif tong == 7:
            hao.append(1)
        elif tong == 8:
            hao.append(0)
        else:  # 9
            hao.append(1)

    que_chinh = _hexagram(hao)
    # Xác định hào động (6 = âm động, 9 = dương động)
    # Gieo lại để xác định hào động chính xác — không, dùng logic gieo
    # Theo phương pháp: mỗi hào có 3 đồng, tổng 6/9 là động
    hao_dong = []
    hao_moi = []
    for i in range(6):
        coins = [secrets.randbelow(2) for _ in range(3)]
        tong = sum(3 if c else 2 for c in coins)
        if tong == 6:
            hao_dong.append(i + 1)
            hao_moi.append(1)  # âm động -> biến thành dương
        elif tong == 9:
            hao_dong.append(i + 1)
            hao_moi.append(0)  # dương động -> biến thành âm
        else:
            hao_moi.append(hao[i])

    # Gán động vào hào chính
    for h in que_chinh["hao"]:
        h["dong"] = h["vi_tri"] in hao_dong

    que_bien = _hexagram(hao_moi) if hao_dong else None
    if que_bien:
        for h in que_bien["hao"]:
            h["dong"] = h["vi_tri"] in hao_dong

    return {"que_chinh": que_chinh, "que_bien": que_bien}


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
    "Nếu cần từ chuyên môn, dùng từ Hán-Việt."
)

SYSTEM_JSON = "Bạn là chuyên gia Kinh Dịch. Chỉ trả về JSON object hợp lệ, không markdown, không giải thích."


def _build_que_info(result: dict[str, Any]) -> str:
    qc = result["que_chinh"]
    qb = result.get("que_bien")
    hao_dong = [h["vi_tri"] for h in qc.get("hao", []) if h.get("dong")]
    lines = [
        f"Quẻ chính: Quẻ {qc['so']} - {qc['ten']} (chủ đề: {qc['chu_de']})",
        f"Thượng quái: {qc['thuong_quai']['ten']} {qc['thuong_quai']['tuong']}",
        f"Hạ quái: {qc['ha_quai']['ten']} {qc['ha_quai']['tuong']}",
    ]
    if hao_dong:
        lines.append(f"Hào động: {hao_dong}")
    else:
        lines.append("Không có hào động")
    if qb:
        lines.append(f"Quẻ biến: Quẻ {qb['so']} - {qb['ten']} (chủ đề: {qb['chu_de']})")
    else:
        lines.append("Không có quẻ biến (6 hào tĩnh)")
    return "\n".join(lines)


async def _prompt_1_core(question: str, que_info: str, context: str) -> str:
    prompt = f"""{LANG_GUARD}

Bạn luận giải Kinh Dịch cho người dùng Việt Nam. Trả lời CỤ THỂ, có ngày tháng, không chung chung.

## Câu hỏi người dùng:
{question}

## Thông tin quẻ:
{que_info}

## Tư liệu về 2 quẻ:
{context}

## Yêu cầu:
Trả về DUY NHẤT JSON object với cấu trúc:

{{
  "tong_quan": "4-6 câu. Tóm tắt tình huống user theo quẻ chính + quẻ biến. Có thể dùng ngày/quý cụ thể.",
  "y_nghia_cot_loi": "5-7 câu. Phân tích BIỂU TƯỢNG quẻ chính (nghĩa tên quẻ, tượng quái, hào động). Ví dụ: 'Mông' nghĩa là non nớt, tượng núi che sông...",
  "xu_huong_bien_hoa": "4-5 câu. Quẻ biến chuyển dịch sang thế nào? Nghĩa tên quẻ biến + hướng đi sắp tới.",
  "phan_tich_theo_cau_hoi": "6-8 câu. Phân tích TRỰC TIẾP câu hỏi user. Nếu user hỏi tài chính → nói cụ thể về đầu tư/tiết kiệm. Nếu hỏi tình duyên → nói cụ thể về mối quan hệ.",
  "theo_linh_vuc": {{
    "tinh_duyen": "2-3 câu (bỏ trống nếu không liên quan)",
    "su_nghiep": "2-3 câu",
    "suc_khoe": "2-3 câu",
    "tai_van": "2-3 câu",
    "hoc_hanh": "2-3 câu"
  }}
}}"""
    return prompt


async def _prompt_2_tam_hop(question: str, que_info: str) -> str:
    prompt = f"""{LANG_GUARD}

Phân tích Tam Hợp (Thiên Thời - Địa Lợi - Nhân Hòa) cho câu hỏi sau. Trả lời CỤ THỂ, có ngày/quý.

## Câu hỏi: {question}
## Quẻ: {que_info}

Trả về DUY NHẤT JSON object:
{{
  "thien_dia_nhan": {{
    "thien_thoi": "4-5 câu. Thời cơ hiện tại có thuận không? Dùng ngày/quý/năm cụ thể.",
    "dia_loi": "4-5 câu. Môi trường, không gian, vị trí có lợi/thất lợi cho user?",
    "nhan_hoa": "4-5 câu. Cần gì từ bản thân và người khác? Nội lực + quan hệ.",
    "tong_ket": "2 câu. Yếu tố nào mạnh/yếu, tập trung vào đâu."
  }}
}}"""
    return prompt


async def _prompt_3_action(question: str, que_info: str) -> str:
    prompt = f"""{LANG_GUARD}

Dựa trên quẻ sau, đề xuất HÀNH ĐỘNG CỤ THỂ cho user.

## Câu hỏi: {question}
## Quẻ: {que_info}

Trả về DUY NHẤT JSON object:
{{
  "goi_y_hanh_dong": [
    "Hành động 1 (cụ thể, có thể làm ngay)",
    "Hành động 2",
    "Hành động 3",
    "Hành động 4"
  ],
  "diem_can_can_nhac": [
    "Điều 1 cần cân nhắc (rủi ro/lưu ý)",
    "Điều 2",
    "Điều 3"
  ],
  "loi_khuyen_thoi_diem": "2-3 câu về thời điểm hành động (ngay/tuần tới/quý tới).",
  "gioi_han": "1 câu: Đây là tham khảo văn hóa, không phải dự đoán chắc chắn."
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


def _clean_obj(obj: Any) -> Any:
    """Đệ quy xoá ký tự Trung khỏi mọi string trong obj."""
    if isinstance(obj, str):
        return _strip_chinese(obj)
    if isinstance(obj, list):
        return [_clean_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean_obj(v) for k, v in obj.items()}
    return obj


async def luan_giai_que(question: str, cast: dict[str, Any] | None = None) -> dict[str, Any]:
    """Luận giải Kinh Dịch bằng 3 prompts song song (nhanh + chất lượng cao)."""
    question = validate_question(question)
    result = cast or gieo_que()
    que_chinh_so = result["que_chinh"]["so"]
    que_bien_so = (result.get("que_bien") or {}).get("so") or que_chinh_so

    context = get_context(que_chinh_so, que_bien_so)
    que_info = _build_que_info(result)

    p1 = await _prompt_1_core(question, que_info, context)
    p2 = await _prompt_2_tam_hop(question, que_info)
    p3 = await _prompt_3_action(question, que_info)

    r1, r2, r3 = await asyncio.gather(
        ollama.generate(p1, system=SYSTEM_JSON, temperature=0.7, json_mode=True, timeout=180.0),
        ollama.generate(p2, system=SYSTEM_JSON, temperature=0.6, json_mode=True, timeout=180.0),
        ollama.generate(p3, system=SYSTEM_JSON, temperature=0.7, json_mode=True, timeout=180.0),
    )

    d1 = _clean_obj(_safe_parse(r1))
    d2 = _clean_obj(_safe_parse(r2))
    d3 = _clean_obj(_safe_parse(r3))

    luan_giai: dict[str, Any] = {}
    luan_giai.update(d1)
    luan_giai.update(d2)
    luan_giai.update(d3)

    return {**result, "cau_hoi": question, "luan_giai": luan_giai}
