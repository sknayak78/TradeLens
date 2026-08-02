#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="${1:-backend}"

if [[ -x "$ROOT_DIR/backend/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
elif [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

run_backend() {
  cd "$ROOT_DIR/backend"
  exec "$PYTHON_BIN" -m pytest "$@"
}

case "$SCOPE" in
  backend)
    shift || true
    run_backend "$@"
    ;;
  frontend)
    cd "$ROOT_DIR/frontend"
    shift || true
    CI=true npm test -- --watchAll=false "$@"
    ;;
  all)
    "$ROOT_DIR/scripts/test.sh" backend
    "$ROOT_DIR/scripts/test.sh" frontend
    ;;
  *)
    echo "Usage: $0 [backend|frontend|all] [test arguments...]" >&2
    exit 64
    ;;
esac
