"""
RAG pipeline — retrieve context từ knowledge base rồi đưa cho LLM.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
import httpx


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


class TuViRAG:
    def __init__(self):
        from vector_store import VectorStore
        self.store = VectorStore()

    async def retrieve_context(self, query: str, top_k: int = 4,
                                max_chars: int = 2500) -> str:
        """Retrieve chunks và format thành context"""
        results = await self.store.search(query, top_k=top_k,
                                            min_similarity=0.35)
        if not results:
            return ""

        parts = []
        current_len = 0
        for i, r in enumerate(results, 1):
            block = (
                f"[Nguồn {i}] {r['section_title']} "
                f"(similarity: {r['similarity']:.2f})\n"
                f"{r['content']}"
            )
            if current_len + len(block) > max_chars:
                break
            parts.append(block)
            current_len += len(block)

        return "\n\n---\n\n".join(parts)

    def build_queries_from_la_so(self, la_so: Dict) -> List[str]:
        """Sinh query từ lá số"""
        queries = []

        for cung in la_so.get("cung", []):
            cung_name = cung.get("cung", "")
            chinh_tinh = cung.get("chinh_tinh", [])
            phu_tinh = cung.get("phu_tinh", [])

            if chinh_tinh:
                stars = ", ".join(s["sao"] for s in chinh_tinh)
                queries.append(f"luận giải cung {cung_name} có {stars}")

            if phu_tinh:
                phu = ", ".join(phu_tinh[:3])
                queries.append(f"cung {cung_name} có {phu}")

        # Nếu không có gì
        if not queries:
            queries.append("luận giải lá số tử vi cơ bản")

        return queries[:6]

    async def analyze_la_so(self, profile: Dict, la_so: Dict,
                              chi_so: Dict) -> Dict:
        """RAG analyze: retrieve context + LLM"""
        # 1. Build queries từ lá số
        queries = self.build_queries_from_la_so(la_so)

        # 2. Retrieve context
        contexts = []
        seen_ids = set()

        for q in queries:
            results = await self.store.search(q, top_k=2, min_similarity=0.35)
            for r in results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    contexts.append(r)

        # Sort by similarity
        contexts.sort(key=lambda x: -x["similarity"])
        contexts = contexts[:6]

        if not contexts:
            # Fallback: không có knowledge base
            return await self._analyze_without_rag(profile, la_so, chi_so)

        # 3. Format context
        context_text = "\n\n---\n\n".join([
            f"[Nguồn {i+1}] {c['section_title']}\n{c['content'][:600]}"
            for i, c in enumerate(contexts)
        ])

        # 4. Prompt cho LLM
        prompt = self._build_rag_prompt(profile, la_so, chi_so, context_text)

        # 5. Call LLM
        try:
            raw = await self._call_llm(prompt)
            result = json.loads(raw)
            result["_sources"] = [
                {
                    "title": c["section_title"],
                    "source": c["source_file"],
                    "similarity": c["similarity"],
                }
                for c in contexts
            ]
            return result
        except Exception as e:
            return {"error": str(e), "raw": raw if 'raw' in dir() else None}

    def _build_rag_prompt(self, profile: Dict, la_so: Dict,
                            chi_so: Dict, context: str) -> str:
        """Prompt RAG"""
        # Rút gọn lá số cho prompt
        la_so_brief = {
            "am_lich": la_so.get("am_lich", ""),
            "can_chi_nam": la_so.get("can_chi_nam", ""),
            "cuc": la_so.get("cuc", ""),
            "menh": la_so.get("menh_chi", ""),
            "than": la_so.get("than_chi", ""),
            "cung": [
                {
                    "ten": c["cung"],
                    "chi": c["dia_chi"],
                    "chinh_tinh": [s["sao"] for s in c.get("chinh_tinh", [])],
                    "phu_tinh": c.get("phu_tinh", [])[:5],
                }
                for c in la_so.get("cung", [])
            ],
        }

        return f"""Bạn là chuyên gia Tử Vi. Luận giải lá số dựa trên TÀI LIỆU THAM KHẢO.

⚠️ QUY TẮC BẮT BUỘC:
1. CHỈ trả lời bằng TIẾNG VIỆT 100%. KHÔNG dùng chữ Hán.
2. CHỈ luận giải dựa trên tài liệu tham khảo + dữ liệu lá số được cung cấp.
3. KHÔNG bịa thêm sao/cung không có trong dữ liệu.
4. Khi tham khảo tài liệu → ghi rõ "theo [Nguồn X]".
5. Nếu không đủ dữ liệu → nói "chưa đủ thông tin để luận giải mục này".

=== TÀI LIỆU THAM KHẢO ===
{context}

=== DỮ LIỆU LÁ SỐ ===
{json.dumps(la_so_brief, ensure_ascii=False, indent=2)}

=== HỒ SƠ NGƯỜI DÙNG ===
- Ngày sinh: {profile.get('ngay_sinh', 'N/A')}
- Can Chi: {profile.get('can_chi_nam', 'N/A')}
- Mệnh: {profile.get('menh_nap_am', 'N/A')}

=== YÊU CẦU OUTPUT ===
Trả về DUY NHẤT JSON:
{{
  "tong_quan": "1-2 câu tổng quan",
  "diem_manh": ["3 mục ngắn gọn, KHÁC NHAU"],
  "diem_can_luu_y": ["2-3 mục ngắn gọn"],
  "cac_cung_noi_bat": [
    {{
      "cung": "Mệnh|Quan Lộc|Tài Bạch|...",
      "luan_giai": "1-2 câu dựa trên dữ liệu có sẵn",
      "hanh_dong": "1 câu hành động cụ thể"
    }}
  ],
  "loi_khuyen_tong_the": "2-3 câu",
  "disclaimer": "Nội dung mang tính tham khảo văn hóa, không phải dự đoán khoa học."
}}

Tối đa 4 cung nổi bật. KHÔNG lặp lại. KHÔNG chữ Hán."""

    async def _call_llm(self, prompt: str) -> str:
        """Gọi Ollama"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 700,
                        "num_ctx": 4096,
                        "top_p": 0.9,
                    },
                    "keep_alive": "10m",
                },
            )
            r.raise_for_status()
            return r.json()["response"]

    async def _analyze_without_rag(self, profile: Dict, la_so: Dict,
                                     chi_so: Dict) -> Dict:
        """Fallback khi knowledge base rỗng"""
        return {
            "tong_quan": "Chưa có đủ tài liệu tham khảo để luận giải chi tiết.",
            "diem_manh": [],
            "diem_can_luu_y": ["Knowledge base chưa được build"],
            "cac_cung_noi_bat": [],
            "loi_khuyen_tong_the": "Vui lòng chạy build_embeddings.py",
            "disclaimer": "Hệ thống đang bảo trì.",
            "_warning": "Knowledge base rỗng — chạy build_embeddings() trước",
        }


# === TEST ===
async def test_rag():
    rag = TuViRAG()
    stats = rag.store.stats()
    print(f"📊 KB stats: {stats}")

    if stats["total_chunks"] == 0:
        print("❌ Knowledge base rỗng!")
        print("   Chạy: python vector_store.py")
        return

    # Test query
    test_queries = [
        "cung Tật Ách Liêm Trinh",
        "cung Mệnh Tử Vi Thiên Cơ",
        "sao Tham Lang tại Dần Thân",
    ]

    for q in test_queries:
        print(f"\n🔍 Query: {q}")
        results = await rag.store.search(q, top_k=2)
        for r in results:
            print(f"   [{r['similarity']:.3f}] {r['section_title']}")
            print(f"   → {r['content'][:100]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rag())