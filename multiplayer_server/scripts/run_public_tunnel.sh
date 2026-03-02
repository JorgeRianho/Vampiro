#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
APP_MODULE="${APP_MODULE:-app:app}"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "Error: uvicorn no esta instalado en este entorno." >&2
  echo "Instala dependencias: pip install -r requirements.txt" >&2
  exit 1
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Error: cloudflared no esta instalado." >&2
  echo "Instalalo y vuelve a ejecutar este script." >&2
  echo "Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
UVICORN_LOG="$TMP_DIR/uvicorn.log"
CLOUDFLARED_LOG="$TMP_DIR/cloudflared.log"

cleanup() {
  if [[ -n "${CLOUDFLARED_PID:-}" ]] && kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
    kill "$CLOUDFLARED_PID" || true
  fi
  if [[ -n "${UVICORN_PID:-}" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

echo "Iniciando servidor en http://$HOST:$PORT ..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" >"$UVICORN_LOG" 2>&1 &
UVICORN_PID=$!

sleep 1
if ! kill -0 "$UVICORN_PID" 2>/dev/null; then
  echo "No se pudo iniciar uvicorn. Log:" >&2
  cat "$UVICORN_LOG" >&2
  exit 1
fi

echo "Creando tunel publico con Cloudflare..."
cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate >"$CLOUDFLARED_LOG" 2>&1 &
CLOUDFLARED_PID=$!

PUBLIC_URL=""
for _ in $(seq 1 40); do
  if ! kill -0 "$CLOUDFLARED_PID" 2>/dev/null; then
    echo "Cloudflared termino antes de crear tunel. Log:" >&2
    cat "$CLOUDFLARED_LOG" >&2
    exit 1
  fi
  if grep -Eo 'https://[-a-zA-Z0-9]+\.trycloudflare\.com' "$CLOUDFLARED_LOG" >/dev/null 2>&1; then
    PUBLIC_URL="$(grep -Eo 'https://[-a-zA-Z0-9]+\.trycloudflare\.com' "$CLOUDFLARED_LOG" | head -n 1)"
    break
  fi
  sleep 0.5
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo "No se pudo extraer la URL publica automaticamente." >&2
  echo "Revisa el log: $CLOUDFLARED_LOG" >&2
  exit 1
fi

echo
echo "Tunel activo."
echo "URL publica: $PUBLIC_URL"
echo "Abre esa URL en el host y ponla en 'URL compartida' antes de crear partida."
echo "Para cerrar: Ctrl+C"
echo

wait "$CLOUDFLARED_PID"
