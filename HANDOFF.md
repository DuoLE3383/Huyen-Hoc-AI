# HANDOFF

## Trạng thái
- Commit: d0a496f
- Backend: 8000 (./start.sh)
- llama-server Vulkan: 8080 (D:\AI\llama.cpp)
- Tunnel: app.huyenbao.com

## Kinh Dịch
- DB: core/huyen_hoc.db (kinh_dich_hanvan + kinh_dich_knowledge)
- RAG: knowledge/kinh_dich_rag.py (v2 ưu tiên)
- Cache: knowledge/kinh_dich_cache.py
- Prompt: divination/kinh_dich.py
- Client: services/ollama_client.py

## Việc tiếp
- Rebuild APK với UI mới
- Test browser end-to-end
- Crawl tuvi.cohoc.net (nếu cần)

## Cảnh báo
- Repo public — chưa rotate secrets
