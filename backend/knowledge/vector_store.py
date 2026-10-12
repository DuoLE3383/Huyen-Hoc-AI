"""
Vector store cho RAG — dùng SQLite + embeddings từ Ollama.
"""
import os
import sqlite3
import json
import struct
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import httpx


DEFAULT_DB = (
    Path(__file__).parent.parent / "data" / "knowledge_base" / "embeddings.db"
)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"


class VectorStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DEFAULT_DB)
        self._init_db()

    def _init_db(self):
        """Tạo bảng nếu chưa có"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE,
                source_file TEXT,
                section_h2 TEXT,
                section_h3 TEXT,
                section_title TEXT,
                chunk_index INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB NOT NULL,
                embedding_dim INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_source 
            ON chunks(source_file)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash 
            ON chunks(content_hash)
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    async def embed_text(self, text: str,
                          max_retries: int = 3) -> List[float]:
        """Tạo embedding từ Ollama"""
        last_err = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(
                        f"{OLLAMA_URL}/api/embeddings",
                        json={"model": EMBED_MODEL, "prompt": text},
                    )
                    r.raise_for_status()
                    data = r.json()
                    if "embedding" not in data:
                        raise ValueError(f"Response thiếu 'embedding': {data}")
                    return data["embedding"]
            except Exception as e:
                last_err = e
                import asyncio
                await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Embedding failed: {last_err}")

    def save_chunk(self, chunk: Dict, embedding: List[float]) -> bool:
        """Lưu chunk + embedding. Return False nếu trùng."""
        content = chunk.get("content", "").strip()
        if not content:
            return False

        content_hash = self._hash(content)

        # Convert embedding to bytes
        emb_bytes = struct.pack(f"{len(embedding)}f", *embedding)

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO chunks 
                (content_hash, source_file, section_h2, section_h3,
                 section_title, chunk_index, content, metadata,
                 embedding, embedding_dim)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_hash,
                chunk.get("metadata", {}).get("source_file", ""),
                chunk.get("section_h2", ""),
                chunk.get("section_h3", ""),
                chunk.get("section_title", ""),
                chunk.get("chunk_index", 0),
                content,
                json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                emb_bytes,
                len(embedding),
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def search(self, query: str, top_k: int = 5,
                     min_similarity: float = 0.3) -> List[Dict]:
        """Tìm chunks liên quan"""
        query_emb = await self.embed_text(query)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT id, source_file, section_h2, section_h3,
                   section_title, content, metadata, embedding, embedding_dim
            FROM chunks
        """)

        results = []
        for row in cursor.fetchall():
            chunk_id, src, h2, h3, title, content, meta, emb_bytes, dim = row

            if dim != len(query_emb):
                continue

            chunk_emb = list(struct.unpack(f"{dim}f", emb_bytes))
            sim = self._cosine_similarity(query_emb, chunk_emb)

            if sim >= min_similarity:
                results.append({
                    "id": chunk_id,
                    "source_file": src,
                    "section_h2": h2,
                    "section_h3": h3,
                    "section_title": title,
                    "content": content,
                    "metadata": json.loads(meta or "{}"),
                    "similarity": round(sim, 4),
                })

        conn.close()
        results.sort(key=lambda x: -x["similarity"])
        return results[:top_k]

    def stats(self) -> Dict:
        """Thống kê"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM chunks")
        total = cursor.fetchone()[0]

        cursor = conn.execute("""
            SELECT source_file, COUNT(*) FROM chunks 
            GROUP BY source_file
        """)
        by_source = dict(cursor.fetchall())

        cursor = conn.execute(
            "SELECT AVG(length(content)) FROM chunks"
        )
        avg_len = cursor.fetchone()[0] or 0

        conn.close()
        return {
            "total_chunks": total,
            "by_source": by_source,
            "avg_content_length": round(avg_len, 1),
        }

    def clear(self):
        """Xóa tất cả"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM chunks")
        conn.commit()
        conn.close()


# === BUILD EMBEDDINGS ===
async def build_embeddings(reset: bool = False):
    """Build embeddings từ tất cả files"""
    import asyncio
    from chunker import MarkdownChunker

    print("🔧 Building embeddings...")

    store = VectorStore()

    if reset:
        print("🗑️  Clearing old embeddings...")
        store.clear()

    # Check Ollama có model không
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            if not any("nomic-embed" in m for m in models):
                print(f"❌ Chưa có model '{EMBED_MODEL}'")
                print(f"   Chạy: ollama pull {EMBED_MODEL}")
                return
            print(f"✅ Ollama OK — có {len(models)} models")
    except Exception as e:
        print(f"❌ Ollama không phản hồi: {e}")
        return

    # Chunk tất cả files
    chunker = MarkdownChunker(max_chunk_size=800, min_chunk_size=80)
    kb_dir = Path(__file__).parent.parent / "data" / "knowledge_base" / "tu_vi"

    all_chunks = []
    for md_file in kb_dir.glob("*.md"):
        chunks = chunker.chunk_file(md_file)
        all_chunks.extend(chunks)
        print(f"📄 {md_file.name}: {len(chunks)} chunks")

    print(f"\n📊 Tổng: {len(all_chunks)} chunks cần embed")

    # Embed từng chunk
    saved = 0
    skipped = 0
    errors = 0

    for i, chunk in enumerate(all_chunks, 1):
        try:
            embedding = await store.embed_text(chunk["content"])
            if store.save_chunk(chunk, embedding):
                saved += 1
            else:
                skipped += 1

            if i % 5 == 0 or i == len(all_chunks):
                print(f"  [{i}/{len(all_chunks)}] "
                      f"saved={saved} skipped={skipped} errors={errors}")
        except Exception as e:
            errors += 1
            print(f"  ❌ Chunk {i}: {e}")

    print(f"\n✅ Done! Stats:")
    stats = store.stats()
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Avg length:   {stats['avg_content_length']} chars")
    print(f"   Files:        {len(stats['by_source'])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(build_embeddings(reset=False))