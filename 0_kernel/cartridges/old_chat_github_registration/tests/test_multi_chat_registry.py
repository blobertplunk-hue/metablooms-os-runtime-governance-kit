from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "multi_chat_registry.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def report(chat_url: str = "https://chatgpt.com/g/g-p-abc/c/old-chat-1") -> dict:
    return {
        "schema": "mb.old_chat_github_registration.report.v1",
        "chat_url": chat_url,
        "source_chat_id": chat_url.rsplit("/", 1)[-1],
        "duplicate_chat_url": False,
        "summary": {"artifact_count": 2, "unshared_count": 2, "missing_local_evidence_count": 1, "conflict_count": 0},
        "artifacts": [],
        "unshared": [
            {"label": "ready", "declared_path": "ready.md", "sha256": sha("ready"), "local_evidence_path": "/tmp/ready.md"},
            {"label": "blocked", "declared_path": "blocked.md", "sha256": sha("blocked")},
        ],
        "missing_local_evidence": [{"label": "blocked", "declared_path": "blocked.md", "sha256": sha("blocked")}],
        "conflicts": [],
        "decision": "PASS_COMPARE_COMPLETE",
    }


def run(tmp_path: Path, payload: dict) -> tuple[int, dict, dict, dict]:
    registry = tmp_path / "registry.json"
    queue = tmp_path / "queue.json"
    report_path = tmp_path / "report.json"
    out_registry = tmp_path / "out_registry.json"
    out_queue = tmp_path / "out_queue.json"
    receipt = tmp_path / "receipt.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    cmd = ["python3", str(TOOL), "--registry", str(registry), "--queue", str(queue), "--report", str(report_path), "--out-registry", str(out_registry), "--out-queue", str(out_queue), "--receipt", str(receipt)]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return proc.returncode, json.loads(out_registry.read_text()), json.loads(out_queue.read_text()), json.loads(receipt.read_text())


def test_ingest_adds_registry_and_promotion_queue(tmp_path: Path) -> None:
    rc, registry, queue, receipt = run(tmp_path, report())
    assert rc == 0
    assert receipt["decision"] == "PASS_INGESTED"
    assert len(registry["chats"]) == 1
    assert len(queue["items"]) == 2
    statuses = {item["label"]: item["status"] for item in queue["items"]}
    assert statuses["ready"] == "READY_FOR_PROMOTION"
    assert statuses["blocked"] == "BLOCKED_MISSING_LOCAL_EVIDENCE"


def test_duplicate_chat_url_warns_and_does_not_duplicate_queue(tmp_path: Path) -> None:
    rc, registry, queue, _receipt = run(tmp_path, report())
    (tmp_path / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (tmp_path / "queue.json").write_text(json.dumps(queue), encoding="utf-8")
    report_path = tmp_path / "report.json"
    out_registry = tmp_path / "out_registry2.json"
    out_queue = tmp_path / "out_queue2.json"
    receipt = tmp_path / "receipt2.json"
    report_path.write_text(json.dumps(report()), encoding="utf-8")
    proc = subprocess.run(["python3", str(TOOL), "--registry", str(tmp_path / "registry.json"), "--queue", str(tmp_path / "queue.json"), "--report", str(report_path), "--out-registry", str(out_registry), "--out-queue", str(out_queue), "--receipt", str(receipt)], text=True, capture_output=True)
    assert proc.returncode == 0
    registry2 = json.loads(out_registry.read_text())
    queue2 = json.loads(out_queue.read_text())
    receipt2 = json.loads(receipt.read_text())
    assert receipt2["decision"] == "WARN_DUPLICATE_CHAT_URL"
    assert len(registry2["chats"]) == 1
    assert len(queue2["items"]) == 2


def test_conflict_adds_blocked_queue_item(tmp_path: Path) -> None:
    payload = report("https://chatgpt.com/g/g-p-abc/c/conflict-chat")
    payload["unshared"] = []
    payload["missing_local_evidence"] = []
    payload["conflicts"] = [{"label": "conflict", "declared_path": "same.md", "sha256": sha("different")}]
    rc, _registry, queue, receipt = run(tmp_path, payload)
    assert rc == 0
    assert receipt["queue_added_blocked"] == 1
    assert queue["items"][0]["status"] == "BLOCKED_PATH_SHA_CONFLICT"


def test_invalid_report_fails_closed(tmp_path: Path) -> None:
    rc, _registry, _queue, receipt = run(tmp_path, {"schema": "bad"})
    assert rc == 2
    assert receipt["decision"] == "FAIL_REPORT_VALIDATION"
    assert receipt["errors"]
