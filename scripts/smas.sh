#!/bin/bash
set -euo pipefail

SMAS_DIR="/Users/yixinzhou/Desktop/SMAS"
cd "$SMAS_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python scripts/openclaw_bridge.py "$@"
