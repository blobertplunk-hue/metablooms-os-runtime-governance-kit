#!/usr/bin/env python3
from __future__ import annotations
import sys
MESSAGE = (
    "claude_memory_sync_writer_v1.py is retired after R4. "
    "Use runtime/governance/python3_S_lane_exec_v1.sh 0_kernel/scripts/session_state_exporter_v1.py instead."
)
print(MESSAGE, file=sys.stderr)
raise SystemExit(64)
