"""
KinhDichLookup — đọc JSON cache, crawl on-demand khi thiếu.
Thread-safe (asyncio lock), có rate limit.
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Any

# ─── Config ────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data" / "kinh_dich"
DATA_DIR.mkdir(parents=True, exist_ok=True)

QUE_FILE = DATA_DIR / "64_que.json"
HAO_FILE = DATA_DIR / "384_hao.json"
NGU_HANH_FILE = DATA_DIR / "ngu_hanh.json"
DUNG_THAN_FILE = DATA_DIR / "dung_than.json"

CRAWL_COOLDOWN = 2.0  # giây giữa 2 lần crawl

# ─── Helpers ───────────────────────────────────────────────────
def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[lookup] Lỗi đọc {path.name}: {e}", flush=True)
        return default if default is not None else {}


def _save_json(path: Path, data: Any) -> None:
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[lookup] Lỗi ghi {path.name}: {e}", flush=True)


# ─── Singleton ─────────────────────────────────────────────────
class KinhDichLookup:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._crawl_lock = asyncio.Lock()
        self._last_crawl_time = 0.0
        self._load()

    def _load(self):
        self.que: dict[str, dict] = _load_json(QUE_FILE, {})
        self.hao: dict[str, dict] = _load_json(HAO_FILE, {})
        self.ngu_hanh: dict[str, dict] = _load_json(NGU_HANH_FILE, {})
        self.dung_than: dict[str, dict] = _load_json(DUNG_THAN_FILE, {})
        print(
            f"[lookup] Loaded {len(self.que)}/64 quẻ, "
            f"{len(self.hao)}/384 hào, "
            f"{len(self.ngu_hanh)} ngũ hành rules, "
            f"{len(self.dung_than)} dụng thần",
            flush=True,
        )

    # ─── Public API ────────────────────────────────────────────
    async def get_ket_luan(
        self,
        que_chinh: int,
        que_bien: int,
        hao_dong: list[int],
        ngu_hanh_que: dict,
        dung_than: str,
    ) -> dict:
        """
        Trả về kết luận đầy đủ — crawl nếu thiếu.
        """
        # 1. Đảm bảo có data 2 quẻ
        await self._ensure_que(que_chinh)
        await self._ensure_que(que_bien)

        # 2. Đảm bảo có data các hào động
        for h in hao_dong:
            await self._ensure_hao(que_chinh, h)

        # 3. Tổng hợp
        # Defensive: ép dung_than về string
        if isinstance(dung_than, dict):
            dung_than = dung_than.get("ten") or dung_than.get("hanh") or ""
        dung_than = str(dung_than).strip() if dung_than else ""

        result = {
            "que_chinh": self.que.get(str(que_chinh), {}),
            "que_bien": self.que.get(str(que_bien), {}),
            "hao_dong": [
                {"so_hao": h, **self.hao.get(f"{que_chinh}.{h}", {})}
                for h in hao_dong
            ],
            "quan_he_ngu_hanh": self._tinh_ngu_hanh(ngu_hanh_que),
            "dung_than": self.dung_than.get(dung_than, {}) if dung_than else {},
        }
        result["ket_luan_tong_hop"] = self._format_ket_luan(result)
        return result

    # ─── Cache + Crawl ─────────────────────────────────────────
    async def _ensure_que(self, so: int) -> None:
        if str(so) in self.que:
            return
        async with self._crawl_lock:
            # Double-check sau khi acquire lock
            if str(so) in self.que:
                return
            await self._rate_limit()
            data = await self._crawl_que(so)
            if data:
                self.que[str(so)] = data
                _save_json(QUE_FILE, self.que)
                print(f"[lookup] ✅ Crawled quẻ {so}: {data.get('ten', '?')}", flush=True)

    async def _ensure_hao(self, que: int, hao: int) -> None:
        key = f"{que}.{hao}"
        if key in self.hao:
            return
        async with self._crawl_lock:
            if key in self.hao:
                return
            await self._rate_limit()
            data = await self._crawl_hao(que, hao)
            if data:
                self.hao[key] = data
                _save_json(HAO_FILE, self.hao)
                print(f"[lookup] ✅ Crawled hào {key}", flush=True)

    async def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_crawl_time
        if elapsed < CRAWL_COOLDOWN:
            await asyncio.sleep(CRAWL_COOLDOWN - elapsed)
        self._last_crawl_time = time.time()

    # ─── Crawl stub (Phase 1) ──────────────────────────────────
    async def _crawl_que(self, so: int) -> dict | None:
        """
        STUB — Phase 1. Sẽ thay bằng crawler thật ở bước 5.
        """
        return {
            "so": so,
            "ten": f"Quẻ {so}",
            "chu_de": "(chưa crawl)",
            "loi_kinh": "",
            "giai_nghia": "",
            "cat_hung": "Trung tính",
            "loi_khuyen": "",
            "_crawled": time.time(),
            "_source": "stub",
        }

    async def _crawl_hao(self, que: int, hao: int) -> dict | None:
        """STUB — Phase 1."""
        return {
            "hao": f"Hào {hao}",
            "loi_kinh": "",
            "giai_nghia": "",
            "cat_hung": "Trung tính",
            "_crawled": time.time(),
            "_source": "stub",
        }

    # ─── Tính toán local ───────────────────────────────────────
    def _tinh_ngu_hanh(self, ngu_hanh_que: dict) -> dict:
        """
        Input: {"thuong": {"hanh": "Moc", "nhat_chu": "Kim"}, "ha": {...}}
        Output: {"thuong": {rule}, "ha": {rule}}
        """
        result = {}
        if not isinstance(ngu_hanh_que, dict):
            return result
        for vi_tri, info in ngu_hanh_que.items():
            if not isinstance(info, dict):
                continue
            hanh_que = info.get("hanh")
            nhat_chu = info.get("nhat_chu")
            # Ép string — tránh unhashable dict
            if isinstance(hanh_que, dict):
                hanh_que = hanh_que.get("ten") or hanh_que.get("hanh") or ""
            if isinstance(nhat_chu, dict):
                nhat_chu = nhat_chu.get("ten") or nhat_chu.get("hanh") or ""
            hanh_que = str(hanh_que).strip() if hanh_que else ""
            nhat_chu = str(nhat_chu).strip() if nhat_chu else ""
            if not hanh_que or not nhat_chu:
                continue
            key = f"{hanh_que}_{nhat_chu}"
            # Thử key chính xác, fallback về tỷ hòa
            rule = self.ngu_hanh.get(key)
            if not rule:
                rule = self.ngu_hanh.get(f"{hanh_que}_{hanh_que}", {})
            result[vi_tri] = {"key": key, **(rule or {})}
        return result

    # ─── Format kết luận ───────────────────────────────────────
    def _format_ket_luan(self, data: dict) -> str:
        parts = []

        qc = data.get("que_chinh", {})
        if qc:
            parts.append(f"**Quẻ chính: {qc.get('ten', '?')}**")
            if qc.get("chu_de"):
                parts.append(f"Chủ đề: {qc['chu_de']}")
            if qc.get("giai_nghia"):
                parts.append(f"Giải nghĩa: {qc['giai_nghia']}")
            if qc.get("cat_hung"):
                parts.append(f"Cát/hung: {qc['cat_hung']}")
            if qc.get("loi_khuyen"):
                parts.append(f"Lời khuyên: {qc['loi_khuyen']}")

        qb = data.get("que_bien", {})
        if qb:
            parts.append(f"\n**Quẻ biến: {qb.get('ten', '?')}**")
            if qb.get("chu_de"):
                parts.append(f"Chủ đề: {qb['chu_de']}")

        hao_list = data.get("hao_dong", [])
        if hao_list:
            parts.append(f"\n**Hào động ({len(hao_list)} hào):**")
            for h in hao_list:
                parts.append(
                    f"- Hào {h.get('so_hao', '?')}: "
                    f"{h.get('giai_nghia', '(chưa có)')} — {h.get('cat_hung', '')}"
                )

        nh = data.get("quan_he_ngu_hanh", {})
        if nh:
            parts.append("\n**Quan hệ ngũ hành:**")
            for vi_tri, info in nh.items():
                if info.get("y_nghia"):
                    parts.append(f"- {vi_tri}: {info['y_nghia']}")

        dt = data.get("dung_than", {})
        if dt:
            parts.append("\n**Dụng thần:**")
            if dt.get("thoi_diem_tot"):
                parts.append(f"- Thời điểm tốt: {dt['thoi_diem_tot']}")
            if dt.get("thoi_diem_xau"):
                parts.append(f"- Thời điểm xấu: {dt['thoi_diem_xau']}")

        return "\n".join(parts) if parts else "(chưa có kết luận)"


# Singleton
lookup = KinhDichLookup()
