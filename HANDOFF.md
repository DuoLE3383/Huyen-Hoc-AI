# HANDOFF — Build Mobile App cho Huyền Học AI

## Mục tiêu session mới
Build iOS + Android app cho Huyền Học AI bằng Capacitor.
Thứ tự: Responsive web (A) → Capacitor setup (B) → Android build (C) → iOS build (D).

## Trả lời 3 câu hỏi đã chốt
1. Apple Developer account: CHƯA có → cần đăng ký $99/năm trước khi build iOS
2. Domain production: Dùng Cloudflare Tunnel (miễn phí) — chưa có domain riêng
3. Thứ tự: A → B → C → D

## Kiến trúc hiện tại
Backend Python FastAPI:
- main.py — assembly
- core/ — auth, database, i18n, notifications, scheduler
- divination/ — tu_vi, tarot, kinh_dich, phong_thuy
- services/ — ollama_client, narrative, action_engine, moi_truong
- analytics/ — ab_testing, analytics, dataset_builder
- routes/ — api.py (85 endpoints), geocode, action_advice, tong_the
- knowledge/ — crawler, chunker, rag, vector_store
- .env — chứa HUYEN_HOC_SECRET_KEY, GEOAPIFY_API_KEY, OPENWEATHER_API_KEY
- huyen_hoc.db — SQLite

Frontend HTML tĩnh:
- index.html, login.html, offline.html, share.html, manifest.json
- pages/ — 15 trang con (dashboard, tuvi, tarot, phong-thuy, ...)
- static/js/ — nav.js, i18n.js, sw.js
- static/icons/icon.svg

Chạy: cd /mnt/d/Documents/GitHub/Huyen Hoc AI && ./start.sh
- Backend: http://localhost:8000
- Frontend: http://localhost:8000/app

Ollama chạy trên Windows host, start.sh tự detect IP.

## Vấn đề tồn đọng
1. Responsive CHƯA có
2. JWT secret 2 file (.env + .env.local)
3. iOS build cần Mac
4. API URL hard-code localhost

## 5 bước cần làm
A. Responsive web (1-2 ngày)
B. Cloudflare Tunnel (2-3 giờ)
C. Capacitor setup (2-3 giờ)
D. Android build (1 ngày)
E. iOS build (2-3 ngày, cần Apple Dev account)

## Lệnh thường dùng
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /mnt/d/Documents/GitHub/Huyen Hoc AI && ./start.sh
pkill -f uvicorn main:app
curl -s http://127.0.0.1:8000/health | python3 -m json.tool

## Lưu ý
- Chạy từng lệnh một, không gộp
- Verify sau mỗi bước
- Backup git tag trước khi sửa nhiều file
- Không đặt biến tên path trong zsh (xung đột PATH)
- WSL2 với /mnt/d/ chậm, cẩn thận CRLF
- Không commit secret key

## Bước đầu tiên cho chat mới
Bắt đầu với Bước A — Responsive web.
1. Đọc file này
2. Test responsive: Chrome DevTools Ctrl+Shift+M
3. Chụp screenshot các trang chính
4. Fix từng trang: /app, /dashboard, /phong-thuy
