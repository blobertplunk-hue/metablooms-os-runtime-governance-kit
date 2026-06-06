#!/usr/bin/env bash
set -euo pipefail
ROOT_DEFAULT="/mnt/data/Metablooms_OS"
ROOT="${METABLOOMS_ROOT:-$ROOT_DEFAULT}"
VENDOR="$ROOT/0_kernel/vendor/python"
if [ -d "$VENDOR" ]; then
  if [ -n "${PYTHONPATH:-}" ]; then
    export PYTHONPATH="$VENDOR:$PYTHONPATH"
  else
    export PYTHONPATH="$VENDOR"
  fi
fi
exec python3 -S "$@"
