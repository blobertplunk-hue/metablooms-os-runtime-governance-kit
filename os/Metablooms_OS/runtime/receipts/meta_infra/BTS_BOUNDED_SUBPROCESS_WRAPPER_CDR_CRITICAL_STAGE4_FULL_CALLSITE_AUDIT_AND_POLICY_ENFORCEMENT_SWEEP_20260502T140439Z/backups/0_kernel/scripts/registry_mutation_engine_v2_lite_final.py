### GOVERNANCE HEADER
# purpose: Apply governed, transaction-safe mutations to artifact registry with full validation, audit, git-backed transaction boundary, and receipts.
# mutation_scope: artifact_registry.json
# invariants_enforced: schema_validation_required, artifact_existence_validation_required, prior_hash_verification_when_available_required, relationship_graph_cycle_detection_required, referential_integrity_required, allowed_state_transition_validation_required, idempotency_key_required, timestamped_backup_required, mutation_receipt_required, atomic_temp_write_then_replace_required, exclusive_file_lock_required, final_state_must_be_validated_before_atomic_commit
# risk_level: mutation-safe
###

import argparse
import difflib
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path("/mnt/data/Metablooms_OS_refined")
REG_PATH = ROOT / "artifact_registry.json"
LOCK_PATH = ROOT / ".registry_mutation.lock"
IDEMPOTENCY_LOG = ROOT / "_idempotency_log.json"
RECEIPT_DIR = ROOT / "_mutation_receipts"
BACKUP_DIR = ROOT / "_registry_backups"

NON_SEMANTIC_FIELDS = {"last_verified", "updated_at", "audit_ts", "audit_timestamp"}

RELATIONSHIP_FIELDS = ["supersedes", "superseded_by", "depends_on", "replaces"]

# Minimal policy: same-status updates are allowed; status changes require transition_reason.
# High-risk demotions/authority changes are not blocked here if explicitly justified,
# but the reason is recorded in the registry and receipt.
SENSITIVE_STATUS_PREFIXES = {
    "primary",
    "active",
    "current",
    "canonical",
    "authoritative",
}

ALLOWED_AUTHORITY_LEVELS = {"low", "medium", "high"}


def ensure_dirs() -> None:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def semantic_clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: semantic_clean(v) for k, v in obj.items() if k not in NON_SEMANTIC_FIELDS}
    if isinstance(obj, list):
        return [semantic_clean(x) for x in obj]
    return obj


def semantic_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(semantic_clean(obj), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def acquire_lock():
    lock_file = LOCK_PATH.open("w")
    fcntl.flock(lock_file, fcntl.LOCK_EX)
    return lock_file


def release_lock(lock_file) -> None:
    fcntl.flock(lock_file, fcntl.LOCK_UN)
    lock_file.close()


def run_git(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=check,
    )


def git_available_and_repo() -> Tuple[bool, str]:
    try:
        run_git(["rev-parse", "--is-inside-work-tree"])
        return True, ""
    except Exception as e:
        return False, repr(e)


def load_idempotency_log() -> Dict[str, Any]:
    if IDEMPOTENCY_LOG.exists():
        return load_json(IDEMPOTENCY_LOG)
    return {}


def write_idempotency_log(log: Dict[str, Any]) -> None:
    tmp = IDEMPOTENCY_LOG.with_suffix(".json.tmp")
    save_json(tmp, log)
    os.replace(tmp, IDEMPOTENCY_LOG)


def validate_request(req: Dict[str, Any]) -> List[str]:
    errors = []
    if not isinstance(req, dict):
        return ["request must be JSON object"]
    for field in ["idempotency_key", "expected_registry_hash", "updates"]:
        if field not in req:
            errors.append(f"request missing field: {field}")
    if "updates" in req and not isinstance(req["updates"], dict):
        errors.append("request.updates must be object")
    if "idempotency_key" in req and not str(req["idempotency_key"]).strip():
        errors.append("idempotency_key must be non-empty")
    return errors


def validate_registry_schema(reg: Dict[str, Any]) -> List[str]:
    errors = []
    if not isinstance(reg, dict):
        return ["registry must be JSON object"]
    if "artifacts" not in reg:
        errors.append("registry missing artifacts")
    elif not isinstance(reg["artifacts"], list):
        errors.append("registry.artifacts must be list")
    else:
        seen = set()
        for idx, a in enumerate(reg["artifacts"]):
            if not isinstance(a, dict):
                errors.append(f"artifact[{idx}] not object")
                continue
            aid = a.get("artifact_id")
            if not aid:
                errors.append(f"artifact[{idx}] missing artifact_id")
            elif aid in seen:
                errors.append(f"duplicate artifact_id: {aid}")
            else:
                seen.add(aid)
            if "authority_level" in a and a["authority_level"] not in ALLOWED_AUTHORITY_LEVELS:
                errors.append(f"{aid}: invalid authority_level {a['authority_level']!r}")
    return errors


def artifact_path(a: Dict[str, Any]) -> Path | None:
    p = a.get("refined_path") or a.get("staged_path") or a.get("path")
    return Path(p) if p else None


def validate_artifact_existence_and_hashes(reg: Dict[str, Any]) -> List[str]:
    errors = []
    for a in reg.get("artifacts", []):
        aid = a.get("artifact_id", "<missing>")
        p = artifact_path(a)
        if p is None:
            continue
        if not p.exists():
            errors.append(f"{aid}: missing file {p}")
            continue
        expected = a.get("refined_sha256") or a.get("staged_sha256") or a.get("source_sha256")
        if expected:
            actual = sha256_file(p)
            if actual != expected:
                errors.append(f"{aid}: hash mismatch expected={expected} actual={actual}")
    return errors


def validate_referential_integrity(reg: Dict[str, Any]) -> List[str]:
    errors = []
    ids = {a.get("artifact_id") for a in reg.get("artifacts", [])}
    for a in reg.get("artifacts", []):
        aid = a.get("artifact_id")
        for field in RELATIONSHIP_FIELDS:
            refs = a.get(field, [])
            if refs is None:
                continue
            if not isinstance(refs, list):
                errors.append(f"{aid}.{field} must be list")
                continue
            for ref in refs:
                if ref not in ids:
                    errors.append(f"{aid}.{field} references missing artifact {ref}")
    return errors


def build_relationship_graph(reg: Dict[str, Any]) -> Dict[str, List[str]]:
    graph = {}
    for a in reg.get("artifacts", []):
        aid = a.get("artifact_id")
        if not aid:
            continue
        edges = []
        for field in ["supersedes", "depends_on", "replaces"]:
            edges.extend(a.get(field, []) or [])
        graph[aid] = list(dict.fromkeys(edges))
    return graph


def validate_no_cycles(reg: Dict[str, Any]) -> List[str]:
    graph = build_relationship_graph(reg)
    errors = []
    visited = set()
    stack = []

    def dfs(node: str):
        if node in stack:
            cycle = " -> ".join(stack[stack.index(node):] + [node])
            errors.append(f"relationship cycle: {cycle}")
            return
        if node in visited:
            return
        visited.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt in graph:
                dfs(nxt)
        stack.pop()

    for node in graph:
        dfs(node)
    return errors


def artifact_by_id(reg: Dict[str, Any], aid: str) -> Dict[str, Any] | None:
    return next((a for a in reg.get("artifacts", []) if a.get("artifact_id") == aid), None)


def status_is_sensitive(status: str | None) -> bool:
    if not status:
        return False
    s = status.lower()
    return any(s.startswith(prefix) or prefix in s for prefix in SENSITIVE_STATUS_PREFIXES)


def validate_state_transitions(before: Dict[str, Any], updates: Dict[str, Any]) -> List[str]:
    errors = []
    for aid, fields in updates.items():
        current = artifact_by_id(before, aid)
        if current is None:
            errors.append(f"{aid}: update target missing")
            continue
        if not isinstance(fields, dict):
            errors.append(f"{aid}: update fields must be object")
            continue
        if "status" in fields:
            old = current.get("status")
            new = fields.get("status")
            if old != new:
                if not fields.get("transition_reason"):
                    errors.append(f"{aid}: status change {old!r} -> {new!r} requires transition_reason")
                if status_is_sensitive(old) or status_is_sensitive(new):
                    if not fields.get("transition_reason"):
                        errors.append(f"{aid}: sensitive status transition requires transition_reason")
        if "authority_level" in fields and fields["authority_level"] not in ALLOWED_AUTHORITY_LEVELS:
            errors.append(f"{aid}: invalid authority_level {fields['authority_level']!r}")
    return errors


def validate_all(reg: Dict[str, Any]) -> List[str]:
    errors = []
    errors.extend(validate_registry_schema(reg))
    errors.extend(validate_artifact_existence_and_hashes(reg))
    errors.extend(validate_referential_integrity(reg))
    errors.extend(validate_no_cycles(reg))
    return errors


def apply_updates(reg: Dict[str, Any], updates: Dict[str, Any]) -> List[str]:
    mutated = []
    for aid, fields in updates.items():
        target = artifact_by_id(reg, aid)
        if target is None:
            raise ValueError(f"artifact not found: {aid}")
        target.update(fields)
        mutated.append(aid)
    return mutated


def unified_diff(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    before_lines = json.dumps(before, indent=2, sort_keys=True).splitlines()
    after_lines = json.dumps(after, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(before_lines, after_lines, fromfile="before", tofile="after", lineterm=""))


def write_registry_temp_and_validate(reg: Dict[str, Any]) -> Path:
    tmp = REG_PATH.with_suffix(".json.tmp")
    save_json(tmp, reg)
    loaded = load_json(tmp)
    errors = validate_all(loaded)
    if errors:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("temp registry validation failed: " + json.dumps(errors, indent=2))
    return tmp


def atomic_replace(tmp: Path) -> None:
    os.replace(tmp, REG_PATH)


def git_commit_transaction(idempotency_key: str, mutated: List[str], before_hash: str, after_hash: str) -> str:
    ok, detail = git_available_and_repo()
    if not ok:
        raise RuntimeError("git repo unavailable: " + detail)

    run_git(["add", "artifact_registry.json"])
    if IDEMPOTENCY_LOG.exists():
        run_git(["add", str(IDEMPOTENCY_LOG.relative_to(ROOT))])
    if RECEIPT_DIR.exists():
        run_git(["add", str(RECEIPT_DIR.relative_to(ROOT))])
    if BACKUP_DIR.exists():
        run_git(["add", str(BACKUP_DIR.relative_to(ROOT))])

    status = run_git(["status", "--short"], check=True).stdout.strip()
    if not status:
        return run_git(["rev-parse", "HEAD"], check=True).stdout.strip()

    message = (
        f"MUTATION {idempotency_key}\n\n"
        f"Mutated: {', '.join(mutated)}\n"
        f"Before: {before_hash}\n"
        f"After: {after_hash}\n"
    )
    run_git(["commit", "-m", message])
    return run_git(["rev-parse", "HEAD"]).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="R23-aligned governed registry mutation engine")
    parser.add_argument("--request", required=True, help="Mutation request JSON")
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit/write")
    args = parser.parse_args()

    ensure_dirs()
    req = load_json(Path(args.request))
    req_errors = validate_request(req)
    if req_errors:
        print("REQUEST VALIDATION FAILED")
        print(json.dumps(req_errors, indent=2))
        return 1

    lock_file = acquire_lock()
    try:
        before = load_json(REG_PATH)
        current_hash = semantic_hash(before)
        if current_hash != req["expected_registry_hash"]:
            print("EXPECTED REGISTRY HASH MISMATCH")
            print("expected:", req["expected_registry_hash"])
            print("actual:", current_hash)
            return 1

        id_log = load_idempotency_log()
        idem_key = req["idempotency_key"]
        if idem_key in id_log:
            print("DUPLICATE IDEMPOTENCY KEY")
            print(json.dumps(id_log[idem_key], indent=2))
            return 0

        pre_errors = validate_all(before)
        pre_errors.extend(validate_state_transitions(before, req["updates"]))
        if pre_errors:
            print("PRE-VALIDATION FAILED")
            print(json.dumps(pre_errors, indent=2))
            return 1

        after = json.loads(json.dumps(before))
        mutated = apply_updates(after, req["updates"])

        post_errors = validate_all(after)
        if post_errors:
            print("POST-VALIDATION FAILED")
            print(json.dumps(post_errors, indent=2))
            return 1

        diff = unified_diff(before, after)
        if args.dry_run:
            print("DRY RUN - NO WRITE, NO GIT COMMIT")
            print(diff if diff else "(no semantic changes)")
            return 0

        # Mark pending before commit; safe replay behavior if interrupted.
        req_hash = semantic_hash(req)
        id_log[idem_key] = {
            "state": "pending",
            "request_hash": req_hash,
            "started_at": time.time(),
        }
        write_idempotency_log(id_log)

        tmp = write_registry_temp_and_validate(after)
        backup_path = BACKUP_DIR / f"registry_backup_{int(time.time())}.json"
        save_json(backup_path, before)

        atomic_replace(tmp)

        committed = load_json(REG_PATH)
        if semantic_hash(committed) != semantic_hash(after):
            raise RuntimeError("post-commit registry verification failed")

        before_hash = semantic_hash(before)
        after_hash = semantic_hash(after)

        # First commit registry + idempotency pending.
        commit_hash = git_commit_transaction(idem_key, mutated, before_hash, after_hash)

        # Finalize idempotency after commit.
        id_log = load_idempotency_log()
        id_log[idem_key] = {
            "state": "committed",
            "request_hash": req_hash,
            "commit_hash": commit_hash,
            "committed_at": time.time(),
        }
        write_idempotency_log(id_log)

        receipt = {
            "idempotency_key": idem_key,
            "commit_hash": commit_hash,
            "mutated_artifacts": mutated,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "request_hash": req_hash,
            "backup_path": str(backup_path),
            "diff": diff,
            "validation": {
                "request": "passed",
                "pre": "passed",
                "post": "passed",
                "temp": "passed",
                "commit": "passed",
            },
            "timestamp": time.time(),
        }
        receipt_path = RECEIPT_DIR / f"mutation_receipt_{int(time.time())}_{idem_key}.json"
        save_json(receipt_path, receipt)

        # Second commit receipt + finalized idempotency, so audit links are in git.
        final_commit = git_commit_transaction(idem_key + "_receipt", mutated, before_hash, after_hash)

        print("MUTATION SUCCESS")
        print("commit_hash:", commit_hash)
        print("audit_commit_hash:", final_commit)
        print("receipt:", receipt_path)
        return 0

    finally:
        release_lock(lock_file)


if __name__ == "__main__":
    raise SystemExit(main())
