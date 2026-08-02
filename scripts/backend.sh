#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="$ROOT_DIR/.env.development"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing development configuration: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -x "$BACKEND_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
elif [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

cd "$BACKEND_DIR"
exec "$PYTHON_BIN" -m uvicorn server:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
