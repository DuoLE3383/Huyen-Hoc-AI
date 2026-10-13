#!/usr/bin/env bash
# start.sh — Huyền Học AI launcher cho Linux/WSL
# Tương đương start.ps1 trên Windows.

set -euo pipefail

# ─── Config ───
MODEL="${1:-qwen2.5:3b}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}ℹ️  $*${NC}"; }
log_ok()    { echo -e "${GREEN}✅ $*${NC}"; }
log_warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_error() { echo -e "${RED}❌ $*${NC}" >&2; }

# ─── Kiểm tra Python ───
if ! command -v python3 >/dev/null 2>&1; then
    log_error "Python 3 không tìm thấy. Cài: sudo apt install python3 python3-venv"
    exit 1
fi

# ─── Kiểm tra Ollama ───
if ! command -v ollama >/dev/null 2>&1; then
    log_warn "Ollama CLI không có trong PATH. Sẽ không tự pull model."
    OLLAMA_AVAILABLE=false
else
    OLLAMA_AVAILABLE=true
fi

# ─── Tạo venv nếu chưa có ───
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    log_info "Tạo virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        log_error "Không tạo được venv."
        exit 1
    fi
fi

VENV_PYTHON="$VENV_DIR/bin/python"

# ─── Cài dependencies ───
log_info "Cài dependencies backend..."
"$VENV_PYTHON" -m pip install -q --upgrade pip
"$VENV_PYTHON" -m pip install -q -r "$PROJECT_DIR/backend/requirements.txt"
log_ok "Dependencies đã cài xong."

# ─── Load / tạo secret key ───
ENV_FILE="$PROJECT_DIR/.env.local"

if [ -z "${HUYEN_HOC_SECRET_KEY:-}" ]; then
    STORED_SECRET=""
    if [ -f "$ENV_FILE" ]; then
        STORED_SECRET=$(grep -E '^HUYEN_HOC_SECRET_KEY=' "$ENV_FILE" | head -n1 | cut -d= -f2- || true)
    fi

    if [ -n "$STORED_SECRET" ]; then
        if [ "${#STORED_SECRET}" -lt 32 ]; then
            log_error ".env.local có HUYEN_HOC_SECRET_KEY ngắn hơn 32 ký tự."
            exit 1
        fi
        export HUYEN_HOC_SECRET_KEY="$STORED_SECRET"
        log_ok "Đã load JWT secret từ .env.local"
    else
        export HUYEN_HOC_SECRET_KEY=$("$VENV_PYTHON" -c "import secrets; print(secrets.token_urlsafe(48))")
        if [ "${#HUYEN_HOC_SECRET_KEY}" -lt 32 ]; then
            log_error "Không tạo được JWT secret hợp lệ."
            exit 1
        fi
        echo "HUYEN_HOC_SECRET_KEY=$HUYEN_HOC_SECRET_KEY" >> "$ENV_FILE"
        log_ok "Đã tạo JWT secret mới, lưu tại .env.local (git-ignored)"
    fi
fi

# ─── Load biến từ .env.local và deploy/.env.prod ───
load_env_var() {
    local var_name="$1"
    local current="${!var_name:-}"
    if [ -n "$current" ]; then
        return 0
    fi
    for f in "$ENV_FILE" "$PROJECT_DIR/deploy/.env.prod"; do
        [ -f "$f" ] || continue
        local line
        line=$(grep -E "^\s*${var_name}\s*=" "$f" | head -n1 || true)
        [ -z "$line" ] && continue
        local value="${line#*=}"
        # Cắt khoảng trắng đầu/cuối
        value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        # Bỏ dấu ngoặc kép nếu có
        value=$(echo "$value" | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")
        # Bỏ qua placeholder
        if [[ "$value" =~ ^(CHANGE|PLACEHOLDER|REPLACE) ]]; then
            continue
        fi
        if [ -n "$value" ]; then
            export "$var_name=$value"
            log_ok "Loaded $var_name từ $(basename "$f")"
            return 0
        fi
    done
    return 1
}

load_env_var TELEGRAM_BOT_TOKEN || true
load_env_var OPENWEATHER_API_KEY || true
load_env_var GEOAPIFY_API_KEY || true

# ─── Ollama URL ───
if [ -z "${OLLAMA_URL:-}" ]; then
    # WSL2: Ollama chạy trên Windows host → cần IP Windows
    if grep -qi microsoft /proc/version 2>/dev/null; then
        WIN_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -n1)
        if [ -n "$WIN_IP" ]; then
            export OLLAMA_URL="http://${WIN_IP}:11434"
            log_info "WSL2 detected → dùng Ollama trên Windows: $OLLAMA_URL"
        else
            export OLLAMA_URL="http://localhost:11434"
            log_warn "Không detect được Windows IP, dùng localhost."
        fi
    else
        export OLLAMA_URL="http://localhost:11434"
    fi
fi

if [ -n "${OLLAMA_MODEL:-}" ]; then
    MODEL="$OLLAMA_MODEL"
else
    export OLLAMA_MODEL="$MODEL"
fi

# ─── Kiểm tra Ollama ready ───
log_info "Kiểm tra Ollama tại $OLLAMA_URL..."
OLLAMA_READY=false
for i in $(seq 1 5); do
    if curl -sf "${OLLAMA_URL%/}/api/tags" >/dev/null 2>&1; then
        OLLAMA_READY=true
        break
    fi
    sleep 1
done

if [ "$OLLAMA_READY" != true ]; then
    log_error "Ollama không phản hồi tại $OLLAMA_URL"
    log_info "Kiểm tra:"
    echo "  1. Ollama đang chạy trên Windows? Mở PowerShell: ollama list"
    echo "  2. Đã set OLLAMA_HOST=0.0.0.0 trên Windows chưa?"
    echo "  3. Firewall Windows cho phép port 11434 chưa?"
    exit 1
fi
log_ok "Ollama đã sẵn sàng."

# ─── Đảm bảo model có sẵn ───
if [ "$OLLAMA_AVAILABLE" = true ]; then
    if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
        log_info "Model '$MODEL' chưa có. Đang pull (có thể mất vài phút)..."
        ollama pull "$MODEL" || {
            log_error "Không pull được model '$MODEL'"
            exit 1
        }
    else
        log_ok "Model '$MODEL' đã có sẵn."
    fi
else
    log_warn "Không có ollama CLI → bỏ qua bước pull model."
    log_warn "Đảm bảo model '$MODEL' đã có trên Windows host."
fi

# ─── Khởi động backend ───
log_ok "Starting Huyền Học AI tại http://localhost:8000/"
echo "   Giữ terminal này mở. Nhấn Ctrl+C để dừng."
echo ""

cd "$PROJECT_DIR/backend"
exec "$VENV_PYTHON" -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload