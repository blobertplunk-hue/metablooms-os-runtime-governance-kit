#!/usr/bin/env python3
"""Compare old-chat claimed artifacts against a GitHub repository manifest."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[a-fA-F0-9]{64}$")
CHAT_URL = re.compile(r"^https://chatgpt\.com/")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL_LOAD_JSON path={path} error={exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL_JSON_OBJECT_REQUIRED path={path}")
    return data


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if packet.get("schema") != "mb.old_chat_github_registration.packet.v1":
        errors.append("packet.schema must be mb.old_chat_github_registration.packet.v1")
    if not isinstance(packet.get("chat_url"), str) or not CHAT_URL.match(packet["chat_url"]):
        errors.append("packet.chat_url must start with https://chatgpt.com/")
    if not isinstance(packet.get("source_chat_id"), str) or not packet["source_chat_id"].strip():
        errors.append("packet.source_chat_id is required")
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("packet.artifacts must be a non-empty list")
        return errors
    for idx, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"artifact[{idx}] must be an object")
            continue
        if not artifact.get("label"):
            errors.append(f"artifact[{idx}].label is required")
        declared_path = artifact.get("declared_path")
        sha256 = artifact.get("sha256")
        if not declared_path and not sha256:
            errors.append(f"artifact[{idx}] needs declared_path or sha256")
        if sha256 is not None and (not isinstance(sha256, str) or not HEX64.match(sha256)):
            errors.append(f"artifact[{idx}].sha256 must be 64 hex chars")
    return errors


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("truncated") is True:
        errors.append("manifest.truncated is true")
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
        return errors
    if manifest.get("file_count") != len(files):
        errors.append("manifest.file_count does not match len(files)")
    seen_paths: set[str] = set()
    for idx, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"manifest.files[{idx}] must be an object")
            continue
        path = item.get("path")
        sha256 = item.get("sha256")
        if not isinstance(path, str) or not path:
            errors.append(f"manifest.files[{idx}].path is required")
        elif path in seen_paths:
            errors.append(f"duplicate manifest path: {path}")
        else:
            seen_paths.add(path)
        if not isinstance(sha256, str) or not HEX64.match(sha256):
            errors.append(f"manifest.files[{idx}].sha256 must be 64 hex chars")
    return errors


def compare(packet: dict[str, Any], manifest: dict[str, Any], known_urls: set[str] | None = None) -> dict[str, Any]:
    known_urls = known_urls or set()
    by_path = {item["path"]: item for item in manifest["files"]}
    by_sha: dict[str, list[dict[str, Any]]] = {}
    for item in manifest["files"]:
        by_sha.setdefault(item["sha256"].lower(), []).append(item)

    artifact_reports: list[dict[str, Any]] = []
    unshared: list[dict[str, Any]] = []
    missing_local_evidence: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for artifact in packet["artifacts"]:
        declared_path = artifact.get("declared_path")
        sha256 = artifact.get("sha256")
        sha_l = sha256.lower() if isinstance(sha256, str) else None
        local_evidence = artifact.get("local_evidence_path")
        path_hit = by_path.get(declared_path) if declared_path else None
        sha_hits = by_sha.get(sha_l, []) if sha_l else []

        if path_hit and sha_l and path_hit["sha256"].lower() == sha_l:
            verdict = "ALREADY_SHARED_BY_PATH_AND_SHA"
        elif path_hit and sha_l and path_hit["sha256"].lower() != sha_l:
            verdict = "PATH_PRESENT_SHA_MISMATCH"
            conflicts.append(artifact)
        elif sha_hits:
            verdict = "ALREADY_SHARED_BY_SHA_DIFFERENT_PATH"
        elif path_hit:
            verdict = "PATH_PRESENT_SHA_UNKNOWN"
        else:
            verdict = "UNSHARED"
            unshared.append(artifact)
            if not local_evidence:
                missing_local_evidence.append(artifact)

        artifact_reports.append({
            "label": artifact.get("label"),
            "declared_path": declared_path,
            "sha256": sha256,
            "verdict": verdict,
            "path_match": path_hit,
            "sha_matches": sha_hits,
        })

    duplicate_url = packet["chat_url"] in known_urls
    return {
        "schema": "mb.old_chat_github_registration.report.v1",
        "chat_url": packet["chat_url"],
        "source_chat_id": packet["source_chat_id"],
        "duplicate_chat_url": duplicate_url,
        "summary": {
            "artifact_count": len(packet["artifacts"]),
            "unshared_count": len(unshared),
            "missing_local_evidence_count": len(missing_local_evidence),
            "conflict_count": len(conflicts),
        },
        "artifacts": artifact_reports,
        "unshared": unshared,
        "missing_local_evidence": missing_local_evidence,
        "conflicts": conflicts,
        "decision": "BLOCKED_DUPLICATE_CHAT_URL" if duplicate_url else "PASS_COMPARE_COMPLETE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--known-url", action="append", default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packet = load_json(args.packet)
    manifest = load_json(args.manifest)
    errors = validate_packet(packet) + validate_manifest(manifest)
    if errors:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"decision": "FAIL_VALIDATION", "errors": errors}, indent=2) + "\n")
        return 2
    report = compare(packet, manifest, set(args.known_url))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
