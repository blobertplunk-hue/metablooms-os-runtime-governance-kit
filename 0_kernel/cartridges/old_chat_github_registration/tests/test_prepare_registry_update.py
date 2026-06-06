from __future__ import annotations

import importlib.util

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'prepare_registry_update.py'
spec = importlib.util.spec_from_file_location('prepare_registry_update', TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def packet(status='COMPLETE_UNVERIFIED'):
    return {
        'schema': 'mb.old_chat_github_registration.work_status_packet.v1',
        'chat_url': 'https://chatgpt.com/c/stage-v-test',
        'source_chat_id': 'stage-v-test',
        'registered_at_utc': '2026-06-05T00:00:00Z',
        'work_summary': 'Stage V test packet',
        'completion_status': status,
        'done_work': [{'label': 'done', 'description': 'completed'}],
        'current_work': [],
        'blockers': [],
        'artifacts': [{'label': 'ready', 'declared_path': 'docs/ready.md', 'sha256': 'a' * 64, 'artifact_status': 'COMPLETE_UNVERIFIED', 'promotion_recommendation': 'CANDIDATE_FOR_REVIEW'}],
        'evidence': [{'label': 'receipt', 'evidence_type': 'RECEIPT', 'reference': 'runtime/receipt.json'}],
        'next_actions': ['compare'],
        'promotion_recommendation': 'CANDIDATE_FOR_REVIEW',
    }


def report():
    return {'schema': 'mb.old_chat_github_registration.report.v1', 'unshared': [{'label': 'ready', 'declared_path': 'docs/ready.md', 'sha256': 'a' * 64, 'local_evidence_path': '/tmp/ready.md'}], 'conflicts': []}


def test_prepare_adds_registry_row_and_ready_queue_item():
    registry = mod.empty_registry('owner/repo')
    queue = mod.empty_queue('owner/repo')
    reg, q, receipt = mod.prepare(packet(), report(), registry, queue, 'owner/repo')
    assert receipt['decision'] == 'PASS_PREPARED_REGISTRY_UPDATE'
    assert reg['registered_chat_count'] == 1
    assert q['queue_item_count'] == 1
    assert q['items'][0]['status'] == 'READY_FOR_PROMOTION'
    assert reg['chats'][0]['packet_path'].endswith('stage-v-test.json')


def test_duplicate_chat_url_different_source_fails():
    registry = mod.empty_registry('owner/repo')
    registry['chats'].append({'chat_url': 'https://chatgpt.com/c/stage-v-test', 'source_chat_id': 'other'})
    try:
        mod.prepare(packet(), report(), registry, mod.empty_queue('owner/repo'), 'owner/repo')
    except SystemExit as exc:
        assert 'duplicate chat_url' in str(exc)
    else:
        raise AssertionError('duplicate chat_url did not fail')


def test_smoke_only_is_not_ready_for_promotion():
    p = packet()
    p['artifacts'][0]['promotion_recommendation'] = 'SMOKE_ONLY_DO_NOT_PROMOTE'
    reg, q, _receipt = mod.prepare(p, report(), mod.empty_registry('owner/repo'), mod.empty_queue('owner/repo'), 'owner/repo')
    assert q['items'][0]['status'] == 'SMOKE_ONLY_DO_NOT_PROMOTE'
    assert reg['queue_counts']['ready_for_promotion'] == 0
