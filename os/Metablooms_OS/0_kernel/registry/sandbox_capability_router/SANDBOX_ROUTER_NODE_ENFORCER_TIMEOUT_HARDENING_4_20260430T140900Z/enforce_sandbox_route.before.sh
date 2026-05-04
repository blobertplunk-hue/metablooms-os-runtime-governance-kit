#!/usr/bin/env bash
set -euo pipefail
ROOT="${METABLOOMS_ROOT:-/mnt/data/Metablooms_OS}"
node "$ROOT/0_kernel/lib/sandbox_router_enforcer_v1.mjs" "${1:-boot_probe}" "${2:-auto}"
