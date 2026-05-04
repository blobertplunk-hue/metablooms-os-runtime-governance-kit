#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, time, importlib.util
from pathlib import Path
TASK_PATTERNS=[('governed_implementation',['implement','patch','fix','repair','code','install','export','validate','test']),('governed_research',['research','web.run','evidence','sources','see','current','latest']),('governed_artifact_generation',['create','generate','build','docx','slides','csv','html','bundle','artifact']),('adaptive',['student','differentiate','scaffold','adaptive','misconception','lesson']),('authentic',['voice','tone','rewrite','authentic','natural','human']),('wit',['funny','witty','humor','playful'])]
TASK_TYPE_MAP={'governed_implementation':'implementation_repair_export','governed_research':'research_and_synthesis','governed_artifact_generation':'artifact_generation','adaptive':'instructional_adaptation','authentic':'voice_and_style','wit':'wit_style'}
def _hash_text(s): return hashlib.sha256(s.encode()).hexdigest()
def select_profile(raw_prompt, root=None):
    txt=raw_prompt.lower(); scores=[]
    for profile,kws in TASK_PATTERNS: scores.append((sum(1 for k in kws if k in txt), profile))
    scores.sort(reverse=True); best=scores[0][1] if scores and scores[0][0]>0 else 'governed_implementation'
    if any(k in txt for k in ['stage','os','metablooms','bundle','checksum','handoff']): best='governed_implementation'
    return best
def optimize_prompt(raw_prompt, root=None, task_hint=None):
    raw=(raw_prompt or '').strip(); profile=task_hint or select_profile(raw, root); task_type=TASK_TYPE_MAP.get(profile,'governed_task')
    needs_web=any(x in raw.lower() for x in ['research','web.run','latest','current','evidence','see'])
    needs_export=any(x in raw.lower() for x in ['export','bundle','zip','checksum','full os'])
    constraints=[]
    if needs_web: constraints.append('Use web.run before making claims that require current or external evidence.')
    if needs_export: constraints.append('Export a full OS ZIP and checksum when validation permits; otherwise write a blocked receipt.')
    constraints += ['Boot from the current authority artifact and verify sidecar before mutation.','Inspect existing artifacts before patching; do not duplicate or overwrite blindly.','Make the smallest code-backed change that restores or improves governed behavior.','Validate with readback plus executable gates before claiming success.','Write receipt, handoff, validation packet, and reusable-index updates.']
    optimized = 'GOVERNED TASK PROMPT - AUTO-OPTIMIZED\n\nProfile: '+profile+'\nTask type: '+task_type+'\n\nOriginal user intent:\n'+raw+'\n\nExecution contract:\n1. Verify current OS authority, checksum sidecar, and canonical root before changing files.\n2. Audit relevant runtime artifacts and identify missing/broken/weak/strong components.\n3. Select tools using the OS method router; prefer safe_walk/coreutils/python3 -S for bounded filesystem work.\n4. Apply the smallest valid code-backed patch or installation; never leave governance as loose documentation.\n5. Validate by direct file readback and behavior tests.\n6. Update telemetry, weakness ledger, reusable asset index, receipts, handoff, and tracker.\n7. Export a full OS bundle with checksum when gates pass; otherwise produce a blocked/partial receipt.\n\nTask-specific constraints:\n- '+'\n- '.join(constraints)+'\n\nRequired output sections:\n- Boot / authority status\n- Gap / weakness findings\n- Patch or installation summary\n- Validation results\n- Export status and artifacts\n- Next governed step\n'
    checks={'has_profile':bool(profile),'has_original_intent':bool(raw),'has_execution_contract':'Execution contract:' in optimized,'has_validation_requirement':'Validate' in optimized,'has_export_rule':'Export' in optimized,'has_receipt_rule':'receipt' in optimized.lower()}
    rationale=['selected_profile_by_keyword_and_os_context:'+profile]
    if not raw: rationale.append('raw_prompt_empty')
    if needs_web: rationale.append('external_evidence_required_by_prompt_terms')
    if needs_export: rationale.append('export_required_by_prompt_terms')
    return {'packet_type':'PROMPT_AUTO_IMPROVEMENT_PACKET_v1','task_type':task_type,'selected_profile':profile,'raw_prompt_hash':_hash_text(raw),'optimized_prompt_hash':_hash_text(optimized),'optimized_prompt':optimized,'improvement_rationale':rationale,'validation_checks':checks,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
def _import_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def run_patch_loop(root, raw_prompt, task_hint=None, write_packet=True):
    root=Path(root); packet=optimize_prompt(raw_prompt, root, task_hint); drift_path=root/'runtime/governance/prompt_engine_drift_gate_v1.py'
    drift=_import_module(drift_path,'prompt_engine_drift_gate_v1').validate_prompt_engine_drift(root, packet) if drift_path.exists() else {'decision':'ALLOW','errors':['drift_gate_missing']}
    packet['drift_gate_decision']=drift; decision='ALLOW' if drift.get('decision')=='ALLOW' and all(packet['validation_checks'].values()) else 'DENY'; packet['decision']=decision
    if write_packet:
        out=root/'runtime/state/PROMPT_PATCH_LEDGER_v1.jsonl'; out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('a',encoding='utf-8') as f: f.write(json.dumps(packet, sort_keys=True)+'\n')
        tel=root/'runtime/governance/prompt_engine_telemetry_v1.py'
        if tel.exists():
            _import_module(tel,'prompt_engine_telemetry_v1').record_prompt_engine_event(root, {'event_type':'prompt_auto_improvement','profile':packet['selected_profile'],'raw_prompt_hash':packet['raw_prompt_hash'],'optimized_prompt_hash':packet['optimized_prompt_hash'],'validator_decision':decision,'drift_flags':drift.get('drift_flags',[])})
    return packet
if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd(); raw=Path(sys.argv[2]).read_text() if len(sys.argv)>2 and Path(sys.argv[2]).exists() else ' '.join(sys.argv[2:])
    r=run_patch_loop(root, raw, write_packet=True); print(json.dumps(r, indent=2)); raise SystemExit(0 if r.get('decision')=='ALLOW' else 1)
