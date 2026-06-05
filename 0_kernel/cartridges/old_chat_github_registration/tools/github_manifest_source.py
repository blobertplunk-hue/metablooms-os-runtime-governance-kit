#!/usr/bin/env python3
"""Build and validate GitHub manifest sources for old-chat registration.

This is the non-workflow fallback path: it can build a complete manifest from a
checked-out repository tree, validate a manifest produced elsewhere, or mark a
known-targeted manifest as partial so downstream stages do not confuse path
probes with a complete repository inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[a-fA-F0-9]{64}$")

DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__"}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object required: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_manifest(root: Path, repository: str | None, ref: str | None, sha: str | None) -> dict[str, Any]:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"root must be an existing directory: {root}")
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if any(part in DEFAULT_EXCLUDED_DIRS for part in rel_parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return {
        "schema": "mb.github.complete_repository_manifest.v2",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": repository,
        "ref": ref,
        "sha": sha,
        "source_kind": "local_checkout_complete",
        "truncated": False,
        "file_count": len(files),
        "files": files,
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
        files = []
    if manifest.get("truncated") is True:
        errors.append("manifest.truncated is true")
    if manifest.get("file_count") != len(files):
        errors.append("manifest.file_count does not match len(files)")
    seen_paths: set[str] = set()
    seen_shas: set[str] = set()
    for idx, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"files[{idx}] must be an object")
            continue
        path = item.get("path")
        sha256 = item.get("sha256")
        bytes_ = item.get("bytes")
        if not isinstance(path, str) or not path:
            errors.append(f"files[{idx}].path is required")
        elif path in seen_paths:
            errors.append(f"duplicate path: {path}")
        else:
            seen_paths.add(path)
        if not isinstance(sha256, str) or not HEX64.match(sha256):
            errors.append(f"files[{idx}].sha256 must be 64 hex chars")
        else:
            seen_shas.add(sha256.lower())
        if not isinstance(bytes_, int) or bytes_ < 0:
            errors.append(f"files[{idx}].bytes must be a nonnegative integer")
    if manifest.get("source_kind") == "targeted_probe_partial":
        warnings.append("manifest source is partial; use only for smoke tests or targeted checks")
    decision = "PASS_COMPLETE_MANIFEST" if not errors and manifest.get("source_kind") != "targeted_probe_partial" else "WARN_PARTIAL_MANIFEST" if not errors else "FAIL_MANIFEST_SOURCE"
    return {
        "schema": "mb.old_chat_github_registration.manifest_source_report.v1",
        "decision": decision,
        "repository": manifest.get("repository"),
        "ref": manifest.get("ref"),
        "sha": manifest.get("sha"),
        "source_kind": manifest.get("source_kind", "unknown"),
        "file_count": len(files),
        "unique_sha_count": len(seen_shas),
        "errors": errors,
        "warnings": warnings,
    }


def mark_targeted_partial(manifest: dict[str, Any]) -> dict[str, Any]:
    out = dict(manifest)
    out["schema"] = out.get("schema", "mb.github.complete_repository_manifest.v2")
    out["source_kind"] = "targeted_probe_partial"
    out["truncated"] = False
    out["file_count"] = len(out.get("files", [])) if isinstance(out.get("files"), list) else 0
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-local")
    build.add_argument("--root", required=True, type=Path)
    build.add_argument("--repository")
    build.add_argument("--ref")
    build.add_argument("--sha")
    build.add_argument("--out", required=True, type=Path)

    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--out", required=True, type=Path)

    partial = sub.add_parser("mark-targeted-partial")
    partial.add_argument("--manifest", required=True, type=Path)
    partial.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    if args.cmd == "build-local":
        write_json(args.out, build_manifest(args.root, args.repository, args.ref, args.sha))
        return 0
    if args.cmd == "validate":
        report = validate_manifest(load_json(args.manifest))
        write_json(args.out, report)
        return 0 if report["decision"] != "FAIL_MANIFEST_SOURCE" else 2
    if args.cmd == "mark-targeted-partial":
        write_json(args.out, mark_targeted_partial(load_json(args.manifest)))
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
