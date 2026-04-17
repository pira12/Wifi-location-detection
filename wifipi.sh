#!/usr/bin/env bash
# Thin wrapper so users run `sudo ./wifipi.sh` from the repo root.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    exec "$SCRIPT_DIR/.venv/bin/python" -m wifipi "$@"
fi
exec python3 -m wifipi "$@"
