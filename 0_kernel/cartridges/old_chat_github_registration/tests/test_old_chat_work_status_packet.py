from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "old_chat_work_status_packet.schema.json").read_text())
FIXTURES = ROOT / "fixtures"


def validate_fixture(name: str) -> None:
    data = json.loads((FIXTURES / name).read_text())
    jsonschema.Draft202012Validator(SCHEMA).validate(data)


def test_finished_verified_fixture_validates() -> None:
    validate_fixture("work_status_finished_verified.json")


def test_in_progress_fixture_validates() -> None:
    validate_fixture("work_status_in_progress.json")


def test_blocked_fixture_validates() -> None:
    validate_fixture("work_status_blocked.json")


def test_invalid_fixture_fails_closed() -> None:
    data = json.loads((FIXTURES / "work_status_invalid.json").read_text())
    errors = sorted(jsonschema.Draft202012Validator(SCHEMA).iter_errors(data), key=lambda e: e.path)
    assert errors


def test_complete_verified_requires_evidence_and_artifact() -> None:
    data = json.loads((FIXTURES / "work_status_finished_verified.json").read_text())
    data["evidence"] = []
    errors = list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors


def test_candidate_for_review_requires_matching_artifact_recommendation() -> None:
    data = json.loads((FIXTURES / "work_status_finished_verified.json").read_text())
    data["artifacts"][0]["promotion_recommendation"] = "NO_PROMOTION"
    errors = list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors
