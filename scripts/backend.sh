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

# shellcheck source=scripts/_python.sh
source "$ROOT_DIR/scripts/_python.sh"
PYTHON_BIN="$(tradelens_resolve_python "$ROOT_DIR")"
tradelens_require_supported_python "$PYTHON_BIN"

cd "$BACKEND_DIR"
exec "$PYTHON_BIN" -m uvicorn server:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
