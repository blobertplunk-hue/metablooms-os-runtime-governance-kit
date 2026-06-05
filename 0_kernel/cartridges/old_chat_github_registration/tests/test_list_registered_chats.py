from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_SCHEMA = json.loads((ROOT / "schemas" / "github_registry_index.schema.json").read_text())
QUEUE_SCHEMA = json.loads((ROOT / "schemas" / "github_promotion_queue.schema.json").read_text())


def test_empty_github_registry_index_fixture_validates() -> None:
    data = json.loads((Path("governance/chat_work_registry/registered_chats.index.json")).read_text())
    Draft202012Validator(REGISTRY_SCHEMA).validate(data)
    assert data["registered_chat_count"] == len(data["chats"])


def test_empty_github_promotion_queue_fixture_validates() -> None:
    data = json.loads((Path("governance/chat_work_registry/promotion_queue.index.json")).read_text())
    Draft202012Validator(QUEUE_SCHEMA).validate(data)
    assert data["queue_item_count"] == len(data["items"])
