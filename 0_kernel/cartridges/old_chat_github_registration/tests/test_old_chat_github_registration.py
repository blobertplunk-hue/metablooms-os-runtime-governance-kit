#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "old_chat_github_registration.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def run_tool(tmp_path: Path, packet: dict, manifest: dict, *extra: str) -> tuple[int, dict]:
    packet_path = write_json(tmp_path / "packet.json", packet)
    manifest_path = write_json(tmp_path / "manifest.json", manifest)
    out = tmp_path / "report.json"
    cmd = ["python3", str(TOOL), "--packet", str(packet_path), "--manifest", str(manifest_path), "--out", str(out), *extra]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return proc.returncode, json.loads(out.read_text())


def manifest_fixture() -> dict:
    files = [
        {"path": "0_kernel/cartridges/existing/README.md", "sha256": sha("existing-readme"), "bytes": 15},
        {"path": "docs/shared_elsewhere.md", "sha256": sha("shared-by-sha"), "bytes": 13},
    ]
    return {
        "schema": "mb.github.complete_repository_manifest.v1",
        "generated_at_utc": "2026-06-05T00:00:00Z",
        "repository": "blobertplunk-hue/metablooms-os-runtime-governance-kit",
        "ref": "refs/heads/main",
        "sha": "abc",
        "truncated": False,
        "file_count": len(files),
        "files": files,
    }


def test_pass_packet_detects_shared_and_unshared(tmp_path: Path) -> None:
    packet = {
        "schema": "mb.old_chat_github_registration.packet.v1",
        "chat_url": "https://chatgpt.com/g/g-p-abc/c/old-chat-1",
        "source_chat_id": "old-chat-1",
        "artifacts": [
            {"label": "already shared exact", "declared_path": "0_kernel/cartridges/existing/README.md", "sha256": sha("existing-readme")},
            {"label": "shared by sha", "declared_path": "docs/renamed.md", "sha256": sha("shared-by-sha")},
            {"label": "new work", "declared_path": "0_kernel/cartridges/new/README.md", "sha256": sha("new-work"), "local_evidence_path": "/tmp/new-work.md"},
        ],
    }
    rc, report = run_tool(tmp_path, packet, manifest_fixture())
    assert rc == 0
    assert report["decision"] == "PASS_COMPARE_COMPLETE"
    assert report["summary"]["unshared_count"] == 1
    verdicts = {item["label"]: item["verdict"] for item in report["artifacts"]}
    assert verdicts["already shared exact"] == "ALREADY_SHARED_BY_PATH_AND_SHA"
    assert verdicts["shared by sha"] == "ALREADY_SHARED_BY_SHA_DIFFERENT_PATH"
    assert verdicts["new work"] == "UNSHARED"


def test_missing_local_evidence_is_reported(tmp_path: Path) -> None:
    packet = {
        "schema": "mb.old_chat_github_registration.packet.v1",
        "chat_url": "https://chatgpt.com/g/g-p-abc/c/old-chat-2",
        "source_chat_id": "old-chat-2",
        "artifacts": [{"label": "new work no evidence", "declared_path": "new.md", "sha256": sha("missing")}],
    }
    rc, report = run_tool(tmp_path, packet, manifest_fixture())
    assert rc == 0
    assert report["summary"]["missing_local_evidence_count"] == 1


def test_path_conflict_is_reported(tmp_path: Path) -> None:
    packet = {
        "schema": "mb.old_chat_github_registration.packet.v1",
        "chat_url": "https://chatgpt.com/g/g-p-abc/c/old-chat-3",
        "source_chat_id": "old-chat-3",
        "artifacts": [{"label": "path conflict", "declared_path": "0_kernel/cartridges/existing/README.md", "sha256": sha("different")}],
    }
    rc, report = run_tool(tmp_path, packet, manifest_fixture())
    assert rc == 0
    assert report["summary"]["conflict_count"] == 1
    assert report["artifacts"][0]["verdict"] == "PATH_PRESENT_SHA_MISMATCH"


def test_invalid_packet_fails_closed(tmp_path: Path) -> None:
    packet = {"schema": "mb.old_chat_github_registration.packet.v1", "chat_url": "bad", "source_chat_id": "bad", "artifacts": [{"label": "bad"}]}
    rc, report = run_tool(tmp_path, packet, manifest_fixture())
    assert rc == 2
    assert report["decision"] == "FAIL_VALIDATION"
    assert report["errors"]


def test_duplicate_url_is_flagged(tmp_path: Path) -> None:
    packet = {
        "schema": "mb.old_chat_github_registration.packet.v1",
        "chat_url": "https://chatgpt.com/g/g-p-abc/c/old-chat-1",
        "source_chat_id": "old-chat-1",
        "artifacts": [{"label": "new", "declared_path": "new.md", "sha256": sha("new")}],
    }
    rc, report = run_tool(tmp_path, packet, manifest_fixture(), "--known-url", "https://chatgpt.com/g/g-p-abc/c/old-chat-1")
    assert rc == 0
    assert report["decision"] == "BLOCKED_DUPLICATE_CHAT_URL"
