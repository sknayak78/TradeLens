#!/usr/bin/env bash
# Shared interpreter resolution and Python-version guard for TradeLens scripts.
#
# Supported runtime: Python >=3.12,<3.14 (3.12 is the validated default).
#
# backend/requirements.txt pins SQLAlchemy==2.0.36, which is not compatible
# with Python 3.14. SQLAlchemy calls typing.Union.__getitem__ unbound; under
# Python 3.14 typing.Union became a class whose __getitem__ is a descriptor, so
# the call raises
#
#   TypeError: descriptor '__getitem__' requires a 'typing.Union' object
#              but received a 'tuple'
#
# while mapping backend/models.py. That surfaces as a confusing SQLAlchemy
# traceback at startup, so the guard below fails early with an actionable
# message instead.

TRADELENS_PYTHON_MIN_MAJOR=3
TRADELENS_PYTHON_MIN_MINOR=12
TRADELENS_PYTHON_MAX_EXCLUSIVE_MAJOR=3
TRADELENS_PYTHON_MAX_EXCLUSIVE_MINOR=14

# Print the interpreter the scripts should use, preferring an explicit venv.
tradelens_resolve_python() {
  local root_dir="$1"
  if [[ -x "$root_dir/backend/venv/bin/python" ]]; then
    printf '%s\n' "$root_dir/backend/venv/bin/python"
  elif [[ -x "$root_dir/venv/bin/python" ]]; then
    printf '%s\n' "$root_dir/venv/bin/python"
  else
    command -v python3
  fi
}

# Exit with a clear message when the interpreter is outside the supported range.
tradelens_require_supported_python() {
  local python_bin="$1"
  local detected=""
  if ! detected="$("$python_bin" -c \
      'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null)"; then
    echo "TradeLens: could not run interpreter '$python_bin'." >&2
    exit 78
  fi

  if ! "$python_bin" -c \
      'import sys; sys.exit(0 if (3, 12) <= sys.version_info[:2] < (3, 14) else 1)' \
      2>/dev/null; then
    {
      echo "TradeLens requires Python >=${TRADELENS_PYTHON_MIN_MAJOR}.${TRADELENS_PYTHON_MIN_MINOR},<${TRADELENS_PYTHON_MAX_EXCLUSIVE_MAJOR}.${TRADELENS_PYTHON_MAX_EXCLUSIVE_MINOR}."
      echo "Detected Python ${detected} at ${python_bin}."
      echo
      echo "SQLAlchemy 2.0.36 is pinned in backend/requirements.txt and does not"
      echo "support Python 3.14, so the backend cannot import backend/models.py."
      echo
      echo "Create backend/venv with Python 3.12 instead:"
      echo "  python3.12 -m venv backend/venv"
      echo "  source backend/venv/bin/activate"
      echo "  ./scripts/backend.sh"
      echo
      echo "See the 'Python runtime' section of README.md."
    } >&2
    exit 78
  fi
}
