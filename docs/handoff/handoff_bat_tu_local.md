# HANDOFF — Huyền Học AI — Bát Tự Local

**Ngày tạo:** 2026-10-15
**Trạng thái:** Bát Tự Local đã hoạt động. Cần debug API `event: core`.

---

## 1. Mục tiêu dự án

- **Dự án:** Huyền Học AI — ứng dụng luận giải Kinh Dịch + Bát Tự.
- **Vấn đề chính:** LLM 7B luận giải sai/thiếu thông tin do dữ liệu đầu vào không đầy đủ.
- **Giải pháp:** Cung cấp sẵn dữ liệu đã tính (Dụng Thần, Thập Thần, Cách cục) cho LLM thay vì để LLM bịa.

---

## 2. Đã hoàn thành

### 2.1. Fix bug Hào động (kinh_dich.py)
- ✅ `_build_que_info()` — đưa "Hào động" lên đầu + marker rõ ràng.
- ✅ Rule 10, 11, 12, 13 trong `NGUYEN_TAC_LUAN_GIAI`:
  - Rule 10: Kiểm tra hào động trước khi viết.
  - Rule 11: Trường `luan_giai_hao_dong` bắt buộc.
  - Rule 12: Tên hào chuẩn (Sơ Lục, Cửu Nhị, ... — KHÔNG bịa Thất Lục, Bát Lục).
  - Rule 13: Dụng Thần phải tính, không bịa.
- Backup: `kinh_dich.py.bak_haodong`, `.bak_rule`.

### 2.2. Fix Can Chi (astrology.py)
- ✅ `tinh_can_chi_nam(year, month=1, day=1)` — dùng `cnlunar` xét Tết âm lịch.
- ✅ `phan_tich_gio_sinh()` — xét giờ Tý đổi ngày.
- Backup: `astrology.py.bak_canchi`.

### 2.3. Module Bát Tự Local
- ✅ `backend/bat_tu/kien_thuc_nen.py`:
  - `CAN_NGU_HANH`, `CHI_NGU_HANH`, `TANG_CAN`.
  - `TUONG_SINH`, `TUONG_KHAC`, `NGU_HOP`.
  - `_thap_than(nhat_chu, can)` — tính Thập Thần.
  - `DUNG_THAN_NHUOC`, `DUNG_THAN_VUONG`, `HOA_CACH_DUNG_THAN`.
- ✅ `backend/bat_tu/dung_than.py`:
  - `tinh_ngu_hanh_count(tu_tru)` — đếm Can + Chi + Tàng Can → %.
  - `nhan_dien_cach_cuc(tu_tru, nhat_chu)` — nhận diện Hóa cách.
  - `tinh_dung_than(nhat_chu, ngu_hanh_percent, cach_cuc)` — Phù Ức.
  - `tinh_thap_than(tu_tru, nhat_chu)` — Thập Thần 4 trụ.

### 2.4. Tích hợp vào lap_tu_tru.py
- ✅ `lap_tu_tru()` — thêm output: `ngu_hanh_percent`, `cach_cuc`, `dung_than`, `thap_than`.
- ✅ `format_bat_tu_context()` — thêm Dụng Thần, Cách cục, Thập Thần vào context gửi LLM.
- Backup: `lap_tu_tru.py.bak_dungthan`.

### 2.5. Cache + Crawler (KHÔNG DÙNG)
- ⚠️ `backend/bat_tu/cache.py` — SQLite cache (đã test OK).
- ⚠️ `backend/bat_tu/crawler_vutruhoc.py` — KHÔNG hoạt động (vutruhoc.vn render JS/RSC, không có API route).
- ⚠️ `backend/bat_tu/service.py` — orchestrate cache + crawl (không dùng).

**Quyết định:** BỎ crawler, dùng local `cnlunar` + `dung_than.py`.

---

## 3. Kết quả test (đã xác thực)

**Input:** 03/03/1983, 17:25, nam.
**Tứ Trụ:** Quý Hợi / Giáp Dần / Canh Dần / Ất Dậu.

### 3.1. Module dung_than.py
