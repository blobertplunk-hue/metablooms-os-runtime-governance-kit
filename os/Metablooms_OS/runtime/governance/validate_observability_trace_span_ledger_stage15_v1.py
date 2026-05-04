#!/usr/bin/env python3
import json, sys, hashlib, subprocess
from pathlib import Path
ROOT=Path('/mnt/data/Metablooms_OS')
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE15_PROMOTED_EVIDENCE_RECOVERY_REPLAY_AND_AUDIT_QUERY_PACKS'
issues=[]
req=[
 '0_kernel/registry/observability/MB_PROMOTED_EVIDENCE_RECOVERY_REPLAY_SCHEMA_v1.json',
 '0_kernel/registry/observability/MB_AUDIT_QUERY_PACK_SCHEMA_v1.json',
 '0_kernel/registry/observability/MB_PROMOTED_EVIDENCE_RECOVERY_REPLAY_POLICY_v1.json',
 'runtime/governance/promoted_evidence_recovery_replay_v1.py',
 'runtime/traces/observability/PROMOTED_EVIDENCE_RECOVERY_REPLAY_LATEST.json',
 'runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.json',
 'runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.md',
 'OPEN_OPERATOR_VISUAL_TRACKER.html']
for rel in req:
    if not (ROOT/rel).exists(): issues.append({'code':'missing_required_artifact','path':rel})
def load(rel):
    return json.load(open(ROOT/rel,encoding='utf-8'))
try:
    replay=load('runtime/traces/observability/PROMOTED_EVIDENCE_RECOVERY_REPLAY_LATEST.json')
    if replay.get('verdict')!='PASS': issues.append({'code':'replay_not_pass','verdict':replay.get('verdict')})
    if len(replay.get('replayed_artifacts',[]))<3: issues.append({'code':'too_few_replayed_artifacts'})
except Exception as e: issues.append({'code':'replay_unreadable','error':str(e)})
try:
    packs=load('runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.json')
    if packs.get('verdict')!='PASS': issues.append({'code':'audit_packs_not_pass','verdict':packs.get('verdict')})
    if len(packs.get('packs',[]))<6: issues.append({'code':'too_few_audit_packs'})
    for p in packs.get('packs',[]):
        if not p.get('results'): issues.append({'code':'audit_pack_empty','query_id':p.get('query_id')})
except Exception as e: issues.append({'code':'audit_packs_unreadable','error':str(e)})
html=(ROOT/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8',errors='ignore') if (ROOT/'OPEN_OPERATOR_VISUAL_TRACKER.html').exists() else ''
for marker in ['stage15-recovery-replay-audit-query-packs','Promoted Evidence Recovery Replay','AUDIT_QUERY_PACKS_LATEST.json']:
    if marker not in html: issues.append({'code':'missing_tracker_marker','marker':marker})
report={'artifact_type':'MB_TRACE_SPAN_LEDGER_STAGE15_RECOVERY_REPLAY_VALIDATION.v1','stage_id':STAGE,'verdict':'PASS' if not issues else 'FAIL','issues':issues}
out=ROOT/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE15_RECOVERY_REPLAY_AUDIT_QUERY_VALIDATION_LATEST.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'issues':len(issues)},sort_keys=True))
sys.exit(0 if not issues else 1)
