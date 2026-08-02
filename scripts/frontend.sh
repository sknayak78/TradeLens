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

cd "$ROOT_DIR/frontend"
exec env PORT="$FRONTEND_PORT" npm start
