import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
if not 512 <= OLLAMA_NUM_CTX <= 32768:
    raise ValueError("OLLAMA_NUM_CTX must be between 512 and 32768.")


def build_analysis_prompt(
    profile: dict[str, Any],
    chi_so: dict[str, float],
    lich_su: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    system = (
        "Bạn tạo nội dung huyền học Việt Nam với mục đích tham khảo, giải trí. "
        "Đưa ra gợi ý thực tế, không khẳng định chắc chắn về tương lai. "
        "Không đưa lời khuyên y tế, pháp lý hoặc tài chính mang tính quyết định. "
        "Chỉ trả về JSON đúng schema được yêu cầu."
    )
    history_text = ""
    if lich_su:
        history_text = "\n\nFEEDBACK ĐÃ GHI NHẬN (chỉ dùng làm ngữ cảnh):\n" + "\n".join(
            f"- {item['loai_su_kien']}: chỉ số {item['du_doan_score']:.0f}, "
            f"người dùng đánh giá {item['thuc_te_score']:.0f}; "
            f"ghi chú: {item.get('ghi_chu') or 'không có'}"
            for item in lich_su[-20:]
        )

    prompt = f"""Hãy tạo một bài phân tích mang tính tham khảo dựa trên hồ sơ sau.

HỒ SƠ:
- Ngày sinh: {profile['ngay_sinh']}
- Can Chi năm: {profile['can_chi_nam']}
- Con giáp: {profile['con_giap']}
- Mệnh nạp âm: {profile['menh_nap_am']}
- Ngũ hành Can/Chi: {profile['ngu_hanh_can']}/{profile['ngu_hanh_chi']}
- Số chủ đạo: {profile['so_chu_dao']}
- Cung phi / Bát quái: {profile['cung_phi']} - {profile['bat_quai']}
- Tam tài: {profile['tam_tai']}

CHỈ SỐ THAM KHẢO (0-100, không phải xác suất):
{json.dumps(chi_so, ensure_ascii=False, indent=2)}
{history_text}

Trả về duy nhất object JSON theo schema:
{{
  "tom_tat": "1-2 câu, không khẳng định chắc chắn",
  "diem_manh": ["..."],
  "diem_yeu": ["..."],
  "hanh_dong_cu_the": [
    {{
      "linh_vuc": "tai_van|tinh_duyen|su_nghiep|suc_khoe|gap_go|thay_doi",
      "muc_do_uu_tien": "cao|trung_binh|thap",
      "hanh_dong": "gợi ý an toàn, cụ thể, tự nguyện",
      "thoi_gian_goi_y": "thời gian gợi ý",
      "vat_pham_ho_tro": "màu sắc/vật phẩm/hướng/con số, nếu phù hợp",
      "ly_do_huyen_hoc": "căn cứ mang tính truyền thống/tham khảo"
    }}
  ],
  "canh_bao": ["điều nên cân nhắc"],
  "cau_chuc": "lời chúc ngắn"
}}

Chỉ trả về JSON, không thêm văn bản khác."""
    return system, prompt


class OllamaClient:
    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model: str = MODEL,
        transport: httpx.AsyncBaseTransport | None = None,
        num_ctx: int = OLLAMA_NUM_CTX,
    ) -> None:
        if not 512 <= num_ctx <= 32768:
            raise ValueError("num_ctx must be between 512 and 32768.")
        self.base_url = base_url
        self.model = model
        self.transport = transport
        self.num_ctx = num_ctx

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()
        generated = result.get("response")
        if not isinstance(generated, str) or not generated.strip():
            raise ValueError("Ollama trả về phản hồi rỗng hoặc sai định dạng.")
        return generated

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"

        timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, transport=self.transport) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as response:
                if response.is_error:
                    await response.aread()
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError("Ollama gửi một chunk JSON không hợp lệ.") from exc
                    if not isinstance(chunk, dict):
                        raise ValueError("Ollama gửi chunk không phải JSON object.")
                    token = chunk.get("response", "")
                    if not isinstance(token, str):
                        raise ValueError("Ollama gửi token không phải chuỗi.")
                    yield {"token": token, "done": bool(chunk.get("done", False))}

    async def phan_tich_va_hanh_dong(
        self,
        profile: dict[str, Any],
        chi_so: dict[str, float],
        lich_su: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        system, prompt = build_analysis_prompt(profile, chi_so, lich_su)
        raw = await self.generate(prompt, system=system, temperature=0.6, json_mode=True)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("Ollama không trả về JSON hợp lệ.") from None
            result = json.loads(raw[start:end])
        if not isinstance(result, dict):
            raise ValueError("JSON do Ollama trả về phải là một object.")
        return result

    async def hieu_chinh_tu_feedback(
        self, feedback_list: list[dict[str, Any]]
    ) -> dict[str, Any]:
        system = (
            "Bạn tóm tắt xu hướng từ phản hồi người dùng. "
            "Không tuyên bố mô hình đã được huấn luyện hoặc thay đổi trọng số thực tế. "
            "Chỉ trả về JSON."
        )
        prompt = f"""Tóm tắt dữ liệu feedback sau và đề xuất hệ số tham khảo (0.5-1.5, 1.0 là trung tính):
{json.dumps(feedback_list, ensure_ascii=False, indent=2)}

Schema:
{{
  "trong_so": {{
    "tai_van": 1.0, "tinh_duyen": 1.0, "su_nghiep": 1.0,
    "suc_khoe": 1.0, "gap_go": 1.0, "thay_doi": 1.0
  }},
  "nhan_xet": "nhận xét ngắn, không khẳng định đây là dự đoán khoa học"
}}
Chỉ JSON."""
        raw = await self.generate(prompt, system=system, temperature=0.3, json_mode=True)
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("JSON do Ollama trả về phải là một object.")
        return result


ollama = OllamaClient()
