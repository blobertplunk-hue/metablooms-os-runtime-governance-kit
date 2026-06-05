from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "github_manifest_source.py"


def test_build_local_manifest_and_validate(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("alpha", encoding="utf-8")
    (repo / "sub").mkdir()
    (repo / "sub" / "b.txt").write_text("beta", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.json"
    subprocess.run(["python3", str(TOOL), "build-local", "--root", str(repo), "--repository", "owner/repo", "--ref", "refs/heads/main", "--sha", "abc", "--out", str(manifest)], check=True)
    data = json.loads(manifest.read_text())
    assert data["source_kind"] == "local_checkout_complete"
    assert data["truncated"] is False
    assert data["file_count"] == 2
    subprocess.run(["python3", str(TOOL), "validate", "--manifest", str(manifest), "--out", str(report)], check=True)
    validation = json.loads(report.read_text())
    assert validation["decision"] == "PASS_COMPLETE_MANIFEST"
    assert validation["errors"] == []


def test_validate_rejects_truncated(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.json"
    manifest.write_text(json.dumps({"schema": "mb.github.complete_repository_manifest.v2", "truncated": True, "file_count": 0, "files": []}), encoding="utf-8")
    proc = subprocess.run(["python3", str(TOOL), "validate", "--manifest", str(manifest), "--out", str(report)], text=True)
    assert proc.returncode == 2
    validation = json.loads(report.read_text())
    assert validation["decision"] == "FAIL_MANIFEST_SOURCE"
    assert "manifest.truncated is true" in validation["errors"]


def test_mark_targeted_partial_warns(tmp_path: Path) -> None:
    digest = hashlib.sha256(b"x").hexdigest()
    manifest = tmp_path / "manifest.json"
    partial = tmp_path / "partial.json"
    report = tmp_path / "report.json"
    manifest.write_text(json.dumps({"schema": "mb.github.complete_repository_manifest.v2", "repository": "owner/repo", "truncated": False, "file_count": 1, "files": [{"path": "x.txt", "sha256": digest, "bytes": 1}]}), encoding="utf-8")
    subprocess.run(["python3", str(TOOL), "mark-targeted-partial", "--manifest", str(manifest), "--out", str(partial)], check=True)
    subprocess.run(["python3", str(TOOL), "validate", "--manifest", str(partial), "--out", str(report)], check=True)
    validation = json.loads(report.read_text())
    assert validation["decision"] == "WARN_PARTIAL_MANIFEST"
    assert validation["warnings"]
