#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, zipfile, hashlib, sys
GUARD_ID="FULL_OS_PORTABLE_EXPORT_MUST_INCLUDE_BASELINE_v1"
def validate_bundle(bundle_path, expected_baseline_sha256, expected_min_bytes=0):
    bundle=Path(bundle_path)
    if not bundle.exists() or not zipfile.is_zipfile(bundle):
        return {"guard_id":GUARD_ID,"decision":"DENY","errors":["bundle_missing_or_not_zip"],"bundle":str(bundle)}
    with zipfile.ZipFile(bundle,"r") as z:
        infos=[i for i in z.infolist() if not i.is_dir()]
        lower=[i.filename.replace("\\","/").lower() for i in infos]
        candidates=[]
        for i in infos:
            n=i.filename.replace("\\","/")
            nl=n.lower()
            if n.endswith(".zip") and ("baseline" in nl or "full_os" in nl or "integrated_os" in nl):
                data=z.read(i)
                candidates.append({"path":n,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    matching=[c for c in candidates if c["sha256"]==expected_baseline_sha256]
    errors=[]
    if not matching: errors.append("missing_current_full_os_baseline_zip_sha")
    elif expected_min_bytes and not any(c["bytes"]>=expected_min_bytes for c in matching): errors.append("baseline_zip_below_expected_min_bytes")
    has_pointer=any("baseline_pointer" in n or "canonical_boot_pointer" in n or "current_full_os_baseline_pointer" in n for n in lower)
    has_tracker=any(n.endswith(".html") and ("tracker" in n or "control_surface" in n) for n in lower)
    has_receipt=any(n.endswith(".json") and ("receipt" in n or "lock" in n) for n in lower)
    has_manifest=any("manifest" in n or "sha256sums" in n or n.endswith(".sha256") for n in lower)
    has_boot=any(("boot" in n or "restore" in n or "verify" in n) and (n.endswith(".py") or n.endswith(".md") or n.endswith(".json") or n.endswith(".sh")) for n in lower)
    if not has_pointer: errors.append("missing_pointer_json")
    if not has_tracker: errors.append("missing_tracker_html")
    if not has_receipt: errors.append("missing_receipt_or_lock_json")
    if not has_manifest: errors.append("missing_manifest_or_sha")
    if not has_boot: errors.append("missing_boot_or_restore_verification_artifact")
    return {"guard_id":GUARD_ID,"decision":"ALLOW" if not errors else "DENY","errors":errors,"candidate_baseline_zips":candidates,"matching_baseline_zips":matching,"required_presence":{"pointer":has_pointer,"tracker":has_tracker,"receipt":has_receipt,"manifest":has_manifest,"boot_or_restore":has_boot}}
if __name__=="__main__":
    if len(sys.argv)<3:
        print("Usage: full_bundle_export_guard_v1.py <bundle.zip> <expected_baseline_sha256> [expected_min_bytes]")
        raise SystemExit(2)
    result=validate_bundle(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 0)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["decision"]=="ALLOW" else 1)
