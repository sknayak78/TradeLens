#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

git -C "$ROOT_DIR" diff --check
find "$ROOT_DIR/scripts" -name '*.sh' -print0 | xargs -0 -n1 bash -n

if [[ -x "$ROOT_DIR/backend/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/backend/venv/bin/python"
elif [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

cd "$ROOT_DIR/backend"
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -m py_compile $(find . -path './venv' -prune -o -name '*.py' -print)

# TypeScript's installed compiler and @types/node versions are currently
# incompatible, so keep this toolkit check dependency-free.  Validate the
# executable JavaScript configuration files without parsing JSX as Node.js.
find "$ROOT_DIR/frontend" \
  -path '*/node_modules/*' -prune -o \
  -path '*/src/*' -prune -o \
  -name '*.js' -print0 | xargs -0 -n1 node --check
