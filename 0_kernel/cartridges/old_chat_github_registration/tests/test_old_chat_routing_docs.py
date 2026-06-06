from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_here_mentions_canonical_registry_paths():
    text = (ROOT / 'START_HERE_FOR_OLD_CHATS.md').read_text()
    assert 'governance/chat_work_registry/registered_chats.index.json' in text
    assert 'governance/chat_work_registry/promotion_queue.index.json' in text
    assert 'GITHUB_FETCH_BLOCKED' in text
    assert 'registration is not promotion' in text.lower()


def test_existing_work_check_requires_overlap_decision():
    text = (ROOT / 'CHECK_EXISTING_WORK_FIRST.md').read_text()
    assert 'Same `chat_url`' in text
    assert 'Same `source_chat_id`' in text
    assert 'Same `declared_path`' in text
    assert 'overlap_decision' in text
    assert 'NEEDS_HUMAN_ADJUDICATION' in text
