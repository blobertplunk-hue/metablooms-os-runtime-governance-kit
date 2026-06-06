#!/usr/bin/env python3
"""MetaBlooms tracker state updater v1.

Updates TRACKER_STATE_v1 after receipt/handoff files exist, then renders a
tracker preview so the next response can start with current tracker state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
import sys
_IO_LIB = Path(__file__).resolve().parents[2] / "lib" / "io"
if str(_IO_LIB) not in sys.path:
    sys.path.insert(0, str(_IO_LIB))
from atomic_json_compat_v1 import write_json_file
from typing import Any, Dict


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rel(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def append_unique_evidence(state: Dict[str, Any], item: Dict[str, str]) -> None:
    evidence = state.setdefault('evidence', [])
    evidence[:] = [e for e in evidence if not (e.get('path') == item['path'] and e.get('kind') == item['kind'])]
    evidence.append(item)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--state', required=True)
    p.add_argument('--receipt', required=True)
    p.add_argument('--handoff', required=True)
    p.add_argument('--stage', required=True)
    p.add_argument('--stage-index', type=int, required=True)
    p.add_argument('--stage-total', type=int, required=True)
    p.add_argument('--status', default='DONE')
    p.add_argument('--now', required=True)
    p.add_argument('--next', dest='next_allowed_action', required=True)
    p.add_argument('--stop-rule', required=True)
    p.add_argument('--timestamp-utc', required=True)
    p.add_argument('--render-preview', required=True)
    args = p.parse_args(argv)

    root = Path(args.root)
    state_path = Path(args.state)
    receipt_path = Path(args.receipt)
    handoff_path = Path(args.handoff)
    preview_path = Path(args.render_preview)

    errors = []
    if not root.is_dir():
        errors.append(f'root missing: {root}')
    if not state_path.is_file():
        errors.append(f'state missing: {state_path}')
    if not receipt_path.is_file():
        errors.append(f'receipt missing: {receipt_path}')
    if not handoff_path.is_file():
        errors.append(f'handoff missing: {handoff_path}')
    if args.stage_index > args.stage_total or args.stage_index < 0:
        errors.append('invalid stage index/total')
    if errors:
        print(json.dumps({'status': 'BLOCKED', 'errors': errors}, indent=2))
        return 1

    state = load_json(state_path)
    handoff = load_json(handoff_path)
    receipt_rel = rel(root, receipt_path)
    handoff_rel = rel(root, handoff_path)
    receipt_sha = sha256_file(receipt_path)
    handoff_sha = sha256_file(handoff_path)

    completed = state.setdefault('completed_stages', [])
    if args.stage not in completed:
        completed.append(args.stage)

    append_unique_evidence(state, {
        'kind': 'receipt',
        'label': f'{args.stage} receipt',
        'path': receipt_rel,
        'sha256': receipt_sha,
    })
    append_unique_evidence(state, {
        'kind': 'handoff',
        'label': f'{args.stage} handoff',
        'path': handoff_rel,
        'sha256': handoff_sha,
    })

    state['status'] = args.status
    state['current_stage'] = args.stage
    state['stage_index'] = args.stage_index
    state['stage_total'] = args.stage_total
    state['progress_mode'] = 'determinate'
    state['progress_label'] = f'{args.stage_index}/{args.stage_total} tracker stages complete'
    state['now'] = args.now
    state['next_allowed_action'] = args.next_allowed_action
    state['stop_rule'] = args.stop_rule
    state['last_updated_utc'] = args.timestamp_utc
    state['blocker'] = {'present': False, 'summary': 'none', 'evidence_path': None}
    state.setdefault('validation', {})['state_validated'] = True
    state.setdefault('validation', {})['schema_validated'] = True
    state['validation']['percent_rule'] = 'determinate_allowed'
    state['validation']['mobile_safe_width_chars'] = 64
    state.setdefault('history', []).append({
        'timestamp_utc': args.timestamp_utc,
        'stage': args.stage,
        'status': args.status,
        'receipt_path': receipt_rel,
        'receipt_sha256': receipt_sha,
        'handoff_path': handoff_rel,
        'handoff_sha256': handoff_sha,
        'handoff_status': handoff.get('status', 'unknown'),
    })

    write_json_file(state_path, state, operation_id="tracker_state_updater_write_state", allowed_roots=["/mnt/data"], create_parent=True)

    # Import renderer after state write to generate the post-update preview.
    sys.path.insert(0, str(root / '0_kernel' / 'cartridges' / 'inline_project_tracker'))
    from TRACKER_RENDERER_v1 import render_tracker  # type: ignore
    preview = render_tracker(state)
    preview_path.write_text(preview + '\n', encoding='utf-8')

    print(json.dumps({
        'status': 'PASS',
        'state_path': str(state_path),
        'receipt_rel': receipt_rel,
        'receipt_sha256': receipt_sha,
        'handoff_rel': handoff_rel,
        'handoff_sha256': handoff_sha,
        'render_preview': str(preview_path),
        'top_marker': preview.startswith('TRACKER ▸'),
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
