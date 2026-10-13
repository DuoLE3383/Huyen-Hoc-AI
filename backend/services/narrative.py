"""AI narration helpers for action advice and combined reports."""

import json
from collections.abc import AsyncIterator
from typing import Any

from services.ollama_client import ollama


SYSTEM_ACTION = """Bạn là trợ lý cung cấp thông tin văn hóa tham khảo.
Chỉ dùng dữ liệu đã cho; không bịa thêm giờ, hướng, thời tiết hoặc sự kiện.
Không khẳng định tương lai và không đưa quyết định y tế, pháp lý hay tài chính.
Viết tiếng Việt rõ ràng, thực tế. Trả về JSON với các khóa tom_tat, ly_do, luu_y."""

SYSTEM_TONG_THE = """Bạn là trợ lý tổng hợp dữ liệu tham khảo về phong thủy, lịch cá nhân,
môi trường và xu hướng. Chỉ dùng dữ liệu đã cho; không bịa thêm hoặc khẳng định tương lai.
Không đưa quyết định y tế, pháp lý hay tài chính. Viết tiếng Việt rõ ràng.
Trả về JSON với các khóa tieu_de, tom_tat, diem_manh, diem_luu_y, hanh_dong."""


def _json_prompt(title: str, data: dict[str, Any], instruction: str) -> str:
    return (
        f"{title}:\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2, default=str)}\n\n"
        f"{instruction}"
    )


def build_action_prompt(data: dict[str, Any]) -> str:
    time_data = data.get("thoi_gian", {})
    place_data = data.get("dia_diem", {})
    compact = {
        "hanh_dong": data.get("hanh_dong"),
        "thoi_gian": {
            "ngay": time_data.get("ngay"),
            "can_chi_ngay": time_data.get("can_chi_ngay"),
            "diem_ngay": time_data.get("diem_tong_hop"),
            "gio_vang": time_data.get("gio_vang"),
            "gio_kieng": time_data.get("gio_kieng"),
        },
        "dia_diem": {
            "thanh_pho": place_data.get("thanh_pho"),
            "quoc_gia": place_data.get("quoc_gia"),
            "huong_nha": place_data.get("huong_nha"),
            "huong_cho_hanh_dong": place_data.get("huong_cho_hanh_dong"),
        },
        "thoi_tiet": data.get("thoi_tiet"),
        "aqi": data.get("aqi"),
        "canh_bao": data.get("canh_bao", []),
        "goi_y_chi_tiet": data.get("goi_y_chi_tiet", []),
    }
    return _json_prompt(
        "Dữ liệu gợi ý hành động",
        compact,
        "Diễn giải ngắn gọn: nên làm gì, khung giờ nào, hướng nào và ở đâu. "
        "Nêu lưu ý thực tế phù hợp với dữ liệu thời tiết và chất lượng không khí. "
        "Không biến đánh giá lịch truyền thống thành khẳng định khoa học.",
    )


def build_tong_the_prompt(data: dict[str, Any]) -> str:
    compact = {
        "phong_thuy": data.get("phong_thuy"),
        "su_kien": data.get("su_kien"),
        "moi_truong": data.get("moi_truong"),
        "moi_truong_ghi_chu": data.get("moi_truong_ghi_chu"),
        "vi_mo": data.get("vi_mo"),
        "profile": data.get("profile"),
        "tong_hop": data.get("tong_hop"),
    }
    return _json_prompt(
        "Dữ liệu tổng hợp",
        compact,
        "Tạo báo cáo có tổng quan, điểm đáng chú ý, điều cần cân nhắc và hành động thực tế. "
        "Phân biệt dữ liệu đo được với diễn giải văn hóa; không khẳng định rằng phong thủy "
        "hoặc xu hướng vĩ mô dự đoán chắc chắn kết quả cá nhân.",
    )


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        first, last = raw.find("{"), raw.rfind("}")
        if first < 0 or last < first:
            raise
        value = json.loads(raw[first:last + 1])
    if not isinstance(value, dict):
        raise ValueError("Phản hồi AI không phải JSON object.")
    return value


async def _stream(
    prompt: str, system: str, fallback: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    tokens: list[str] = []
    try:
        async for chunk in ollama.generate_stream(
            prompt, system=system, temperature=0.5, json_mode=True, timeout=300
        ):
            token = chunk.get("token", "")
            if token:
                tokens.append(token)
                yield {"type": "token", "content": token}
            if chunk.get("done"):
                break
        try:
            parsed = _parse_json("".join(tokens))
        except (json.JSONDecodeError, ValueError):
            parsed = {**fallback, "tom_tat": "".join(tokens)}
        yield {"type": "done", "parsed": parsed}
    except Exception as exc:
        yield {"type": "error", "message": str(exc)}


async def stream_action_narrative(data: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    fallback = {"tom_tat": data.get("ket_luan", ""), "ly_do": "", "luu_y": []}
    async for event in _stream(build_action_prompt(data), SYSTEM_ACTION, fallback):
        yield event


async def generate_action_narrative(data: dict[str, Any]) -> dict[str, Any]:
    raw = await ollama.generate(
        build_action_prompt(data), system=SYSTEM_ACTION, temperature=0.5, json_mode=True,
        timeout=300,
    )
    return _parse_json(raw)


async def generate_tong_the_narrative(data: dict[str, Any]) -> dict[str, Any]:
    raw = await ollama.generate(
        build_tong_the_prompt(data), system=SYSTEM_TONG_THE, temperature=0.5,
        json_mode=True, timeout=300,
    )
    return _parse_json(raw)


async def stream_tong_the_narrative(data: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    fallback = {
        "tieu_de": "Báo cáo tổng hợp",
        "tom_tat": "",
        "diem_manh": [],
        "diem_luu_y": [],
        "hanh_dong": [],
    }
    async for event in _stream(build_tong_the_prompt(data), SYSTEM_TONG_THE, fallback):
        yield event
