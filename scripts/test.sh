#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="${1:-backend}"

# shellcheck source=scripts/_python.sh
source "$ROOT_DIR/scripts/_python.sh"

run_backend() {
  # Guarded here rather than at the top so the `frontend` scope keeps working
  # without a supported Python interpreter.
  local python_bin
  python_bin="$(tradelens_resolve_python "$ROOT_DIR")"
  tradelens_require_supported_python "$python_bin"
  cd "$ROOT_DIR/backend"
  exec "$python_bin" -m pytest "$@"
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
