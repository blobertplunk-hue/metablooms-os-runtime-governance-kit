#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]
idx = json.loads((ROOT / "recovery/RECOVERY_INDEX.json").read_text())
loc = json.loads((ROOT / "recovery/ARTIFACT_LOCATOR.json").read_text())
assert re.match(r"^[0-9a-f]{64}$", idx["latest_boot_authority"]["sha256"])
assert idx["latest_boot_authority"]["portable_boot_verify_status"] == "PASS"
assert idx["next_authorized_stage"]
assert loc["locator_id"] == "ARTIFACT_LOCATOR_STAGE43A2_v1"
print("PASS: recovery index and artifact locator valid")
