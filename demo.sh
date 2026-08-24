#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/generate_fixtures.py >/dev/null
exec python3 -m krishi_vani.server --host "${KRISHI_HOST:-127.0.0.1}" --port "${KRISHI_PORT:-8787}"
