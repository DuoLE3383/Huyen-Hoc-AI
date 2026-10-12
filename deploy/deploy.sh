#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ ! -f .env.prod ]; then
    echo "Missing deploy/.env.prod. Copy .env.prod.example and configure it first." >&2
    exit 1
fi

set -a
. ./.env.prod
set +a
: "${OLLAMA_MODEL:=qwen2.5:7b}"

if [ "${DOMAIN:-}" = "example.com" ] || [ -z "${DOMAIN:-}" ]; then
    echo "Set DOMAIN to the real production domain in deploy/.env.prod." >&2
    exit 1
fi
if [ -z "${HUYEN_HOC_SECRET_KEY:-}" ] || [ "${#HUYEN_HOC_SECRET_KEY}" -lt 32 ]; then
    echo "HUYEN_HOC_SECRET_KEY must contain at least 32 characters." >&2
    exit 1
fi

docker compose --env-file .env.prod -f docker-compose.yml build backend
docker compose --env-file .env.prod -f docker-compose.yml up -d

echo "Waiting for the backend health check..."
healthy=0
for _ in $(seq 1 30); do
    if docker compose --env-file .env.prod -f docker-compose.yml exec -T backend \
        curl --fail --silent http://localhost:8000/health >/dev/null; then
        healthy=1
        break
    fi
    sleep 2
done

if [ "$healthy" -ne 1 ]; then
    docker compose --env-file .env.prod -f docker-compose.yml logs --tail=100 backend
    echo "Backend did not become healthy." >&2
    exit 1
fi

echo "Waiting for Ollama..."
ollama_ready=0
for _ in $(seq 1 30); do
    if docker compose --env-file .env.prod -f docker-compose.yml exec -T ollama \
        ollama list >/dev/null 2>&1; then
        ollama_ready=1
        break
    fi
    sleep 2
done

if [ "$ollama_ready" -ne 1 ]; then
    echo "Ollama did not become ready." >&2
    exit 1
fi

if ! docker compose --env-file .env.prod -f docker-compose.yml exec -T ollama \
    ollama list | grep -Fq "$OLLAMA_MODEL"; then
    echo "Pulling configured Ollama model: $OLLAMA_MODEL"
    docker compose --env-file .env.prod -f docker-compose.yml exec -T ollama \
        ollama pull "$OLLAMA_MODEL"
fi

echo "Deployment started for ${DOMAIN}; inspect logs with docker compose logs -f."
