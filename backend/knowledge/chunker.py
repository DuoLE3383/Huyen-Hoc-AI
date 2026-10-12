"""
Chunk markdown theo section để embedding.
Giữ context và metadata.
"""
import re
from pathlib import Path
from typing import List, Dict, Optional


class MarkdownChunker:
    def __init__(self, max_chunk_size: int = 800, min_chunk_size: int = 80,
                 overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap

    def parse_frontmatter(self, content: str) -> tuple:
        """Tách frontmatter và body"""
        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip().strip('"')
                return metadata, parts[2]
        return {}, content

    def chunk_file(self, filepath: Path) -> List[Dict]:
        """Chunk file theo heading cấu trúc"""
        content = filepath.read_text(encoding="utf-8")
        metadata, body = self.parse_frontmatter(content)

        # Thêm source_file vào metadata
        metadata["source_file"] = filepath.name

        chunks = []
        current_h2 = ""
        current_h3 = ""
        buffer = []

        lines = body.split("\n")

        for line in lines:
            h1_match = re.match(r"^#\s+(.+)$", line)
            h2_match = re.match(r"^##\s+(.+)$", line)
            h3_match = re.match(r"^###\s+(.+)$", line)

            if h1_match:
                # H1 = title chính → skip
                continue

            if h2_match:
                # Save section cũ
                if buffer:
                    self._save_chunk(chunks, metadata, current_h2,
                                     current_h3, buffer)
                current_h2 = h2_match.group(1).strip()
                current_h3 = ""
                buffer = []

            elif h3_match:
                # Save sub-section cũ
                if buffer:
                    self._save_chunk(chunks, metadata, current_h2,
                                     current_h3, buffer)
                current_h3 = h3_match.group(1).strip()
                buffer = []

            else:
                if line.strip():
                    buffer.append(line)

        # Save cuối
        if buffer:
            self._save_chunk(chunks, metadata, current_h2, current_h3, buffer)

        return chunks

    def _save_chunk(self, chunks: List, metadata: Dict,
                    h2: str, h3: str, buffer: List[str]):
        """Lưu chunk vào list"""
        content = "\n".join(buffer).strip()

        if len(content) < self.min_chunk_size:
            return

        # Tạo title cho chunk
        title_parts = []
        if h2:
            title_parts.append(h2)
        if h3:
            title_parts.append(h3)
        section_title = " › ".join(title_parts) if title_parts else "Chung"

        # Nếu content quá dài → split
        if len(content) > self.max_chunk_size:
            sub_chunks = self._split_text(content)
            for i, sub in enumerate(sub_chunks):
                chunks.append({
                    "section_h2": h2,
                    "section_h3": h3,
                    "section_title": section_title,
                    "chunk_index": i,
                    "total_sub_chunks": len(sub_chunks),
                    "content": sub,
                    "content_length": len(sub),
                    "metadata": metadata.copy(),
                })
        else:
            chunks.append({
                "section_h2": h2,
                "section_h3": h3,
                "section_title": section_title,
                "chunk_index": 0,
                "total_sub_chunks": 1,
                "content": content,
                "content_length": len(content),
                "metadata": metadata.copy(),
            })

    def _split_text(self, text: str) -> List[str]:
        """Split đoạn dài theo câu"""
        # Split theo dấu câu
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""

        for sent in sentences:
            if not sent.strip():
                continue
            if len(current) + len(sent) + 1 > self.max_chunk_size:
                if current.strip():
                    chunks.append(current.strip())
                # Overlap: giữ vài câu cuối của chunk trước
                if chunks and self.overlap > 0:
                    overlap_text = chunks[-1][-self.overlap:]
                    current = overlap_text + " " + sent
                else:
                    current = sent
            else:
                current = (current + " " + sent).strip()

        if current.strip():
            chunks.append(current.strip())

        return chunks


# === SỬ DỤNG ===
if __name__ == "__main__":
    chunker = MarkdownChunker(max_chunk_size=800, min_chunk_size=80)
    kb_dir = Path(__file__).parent.parent / "data" / "knowledge_base" / "tu_vi"

    all_chunks = []
    for md_file in kb_dir.glob("*.md"):
        chunks = chunker.chunk_file(md_file)
        all_chunks.extend(chunks)
        print(f"📄 {md_file.name}: {len(chunks)} chunks")

    print(f"\n📊 Tổng: {len(all_chunks)} chunks")
    if all_chunks:
        print(f"\n📋 Sample chunk:")
        sample = all_chunks[0]
        print(f"   Section: {sample['section_title']}")
        print(f"   Length: {sample['content_length']} chars")
        print(f"   Content: {sample['content'][:200]}...")