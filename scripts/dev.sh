#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env.development"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing development configuration: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

cleanup() {
  trap - INT TERM EXIT
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

"$ROOT_DIR/scripts/backend.sh" &
BACKEND_PID=$!
"$ROOT_DIR/scripts/frontend.sh" &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
