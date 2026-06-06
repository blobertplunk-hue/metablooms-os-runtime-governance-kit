#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import json, time, shutil
GATE_ID = "GOVERNANCE_SURVIVAL_PROMOTION_GATE_v1.0"

def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def resolve_root(start: str | Path) -> Path:
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    candidates = [p, p / 'Metablooms_OS', p.parent]
    cur = p
    for _ in range(10):
        candidates.append(cur)
        cur = cur.parent
    for c in candidates:
        if (c / '0_kernel').exists() and (c / 'runtime').exists():
            return c
    return p

def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {'_load_error': f'{type(exc).__name__}: {exc}'}

def _exists(root: Path, rel: str) -> bool:
    return bool(rel) and (root / rel).exists()

def scan_unregistered_active_governance(root: Path, registered: set[str]) -> List[str]:
    # Bounded active-surface scan only. Do not recursively walk historical
    # evidence trees during chat-turn governance; that is handled by export audit.
    active_dirs = ['0_kernel/chat_governance','0_kernel/sandbox_governance','0_kernel/tool_governance','runtime/governance']
    loose: List[str] = []
    keywords = ('governance','gate','router','kernel','policy','invariant','selector','promotion','blocker')
    for sr in active_dirs:
        base = root / sr
        if not base.exists():
            continue
        for p in base.glob('*'):
            if not p.is_file():
                continue
            rel = str(p.relative_to(root))
            if rel in registered:
                continue
            if any(k in p.name.lower() for k in keywords):
                loose.append(rel)
    return sorted(loose)

def validate(root: str | Path, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = dict(context or {})
    r = resolve_root(root)
    errors: List[str] = []
    warnings: List[str] = []
    manifest_rel = '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json'
    manifest_path = r / manifest_rel
    if not manifest_path.exists():
        errors.append('missing_boot_required_gate_manifest')
        manifest: Dict[str, Any] = {}
    else:
        manifest = _load_json(manifest_path)
        if manifest.get('_load_error'):
            errors.append('invalid_boot_required_gate_manifest:' + manifest['_load_error'])
    required = list(manifest.get('critical_governance_paths', []))
    sim_missing = set(context.get('simulate_missing_paths', []))
    for rel in required:
        if rel in sim_missing or not _exists(r, rel):
            errors.append('missing_required_governance_path:' + rel)
    hard_required = [
        'runtime/governance/chat_governance_kernel_v1.py',
        'runtime/governance/tool_selection_evidence_router_v1.py',
        'runtime/governance/sandbox_tool_governance_v1.py',
        'runtime/governance/governance_survival_promotion_gate_v1.py',
        '0_kernel/sandbox_governance/SANDBOX_TOOL_USE_POLICY_v1.json',
        '0_kernel/registry/PROMOTION_BLOCKERS_v1.json',
        '0_kernel/registry/GOVERNANCE_SCATTER_AUDIT_v1.json'
    ]
    for rel in hard_required:
        if rel in sim_missing or not _exists(r, rel):
            errors.append('missing_hard_required_path:' + rel)
    registered = set(required)
    if context.get('deny_unregistered_governance', True):
        loose = scan_unregistered_active_governance(r, registered)
        if context.get('simulate_unregistered_governance_file'):
            loose.append(str(context.get('simulate_unregistered_governance_file')))
        if loose:
            errors.append('unregistered_active_governance_file:' + loose[0])
            if len(loose) > 1:
                warnings.append(f'unregistered_active_governance_file_count:{len(loose)}')
    if context.get('tool_use_requested') and not context.get('tool_selection_packet'):
        errors.append('missing_tool_selection_packet_before_tool_use')
    if context.get('cartridge_execution_requested') and not context.get('router_decision'):
        errors.append('missing_router_decision_before_cartridge_execution')
    if context.get('SEE_required'):
        if not context.get('web_run_evidence'):
            errors.append('missing_web_run_evidence_for_required_SEE')
        if not context.get('SEE_artifact'):
            errors.append('missing_SEE_artifact_when_required')
    if context.get('SEE_completed') and not context.get('CE_artifact'):
        errors.append('missing_CE_artifact_after_SEE')
    if context.get('final_response'):
        if not context.get('tracker_preview'):
            errors.append('missing_tracker_preview_before_final_response')
        if not context.get('receipt_artifact'):
            errors.append('missing_receipt_before_final_response')
        if not context.get('handoff_artifact'):
            errors.append('missing_handoff_before_final_response')
    if context.get('promotion_requested'):
        for key in ['complete_os_export_written','duplicate_free_zip_validation_passed','zip_integrity_test_passed','targeted_fresh_extract_smoke_passed','behavior_tests_passed','checksum_sidecar_written']:
            if not context.get(key):
                errors.append('promotion_blocked_missing_' + key)
    return {
        'gate_id': GATE_ID,
        'checked_utc': _now(),
        'root': str(r),
        'decision': 'DENY' if errors else 'ALLOW',
        'errors': errors,
        'warnings': warnings,
        'required_count': len(required)
    }

def main(argv: List[str] | None = None) -> int:
    import sys
    argv = list(argv or sys.argv[1:])
    root = argv[0] if argv else '.'
    context = {}
    if len(argv) > 1:
        context = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    res = validate(root, context)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res['decision'] == 'ALLOW' else 2

if __name__ == '__main__':
    raise SystemExit(main())
