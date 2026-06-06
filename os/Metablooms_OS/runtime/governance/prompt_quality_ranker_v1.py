#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, time, re
from pathlib import Path

WEIGHTS={"contract_compliance":0.20,"evidence_binding":0.15,"validation_strength":0.20,"task_fit":0.15,"specificity":0.10,"artifact_discipline":0.15,"regression_risk":0.05}
REQUIRED_PHRASES=["Original user intent:","Execution contract:","Validate","receipt","handoff"]

def _norm(s): return (s or '').strip()
def _hash(s): return hashlib.sha256(_norm(s).encode()).hexdigest()
def hard_gate_check(candidate:dict)->dict:
    text=_norm(candidate.get('optimized_prompt') or candidate.get('prompt') or '')
    raw=_norm(candidate.get('raw_prompt') or candidate.get('original_prompt') or '')
    errors=[]
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in text.lower(): errors.append('missing_required_phrase:'+phrase)
    if raw and raw[:30].lower() not in text.lower():
        # tolerate summarized intent when exact prefix is not preserved
        if 'original user intent' not in text.lower(): errors.append('original_intent_not_preserved')
    if any(k in raw.lower() for k in ['export','zip','bundle','checksum','full os']) and 'export' not in text.lower(): errors.append('export_rule_missing_for_export_task')
    if 'option' in raw.lower() and 'best-to-worst' not in text.lower() and 'best to worst' not in text.lower(): errors.append('best_to_worst_rule_missing_for_option_task')
    return {'allow': not errors, 'errors': errors}

def score_candidate(candidate:dict, fixture:dict|None=None)->dict:
    text=_norm(candidate.get('optimized_prompt') or candidate.get('prompt') or '')
    raw=_norm(candidate.get('raw_prompt') or candidate.get('original_prompt') or '')
    lower=text.lower(); raw_lower=raw.lower()
    gates=hard_gate_check(candidate)
    dims={}
    dims['contract_compliance']=sum(1 for p in REQUIRED_PHRASES if p.lower() in lower)/len(REQUIRED_PHRASES)
    dims['evidence_binding']=1.0 if any(x in lower for x in ['web.run','evidence','see','source','citation']) else (0.6 if not any(x in raw_lower for x in ['research','current','latest','evidence','web.run']) else 0.2)
    dims['validation_strength']=min(1.0, sum(1 for x in ['validate','test','fixture','replay','readback','gate'] if x in lower)/4)
    dims['task_fit']=1.0 if (not raw or any(tok in lower for tok in re.findall(r'[a-zA-Z]{5,}', raw_lower)[:8])) else 0.6
    dims['specificity']=min(1.0, (len(re.findall(r'\b[A-Z0-9_]{4,}\b', text))*0.08)+(len(text)/1800))
    dims['artifact_discipline']=min(1.0, sum(1 for x in ['artifact','receipt','handoff','checksum','bundle','ledger','index'] if x in lower)/5)
    dims['regression_risk']=1.0 if gates['allow'] else 0.0
    weighted=sum(dims[k]*WEIGHTS[k] for k in WEIGHTS)
    return {'candidate_id':candidate.get('candidate_id') or candidate.get('id') or _hash(text)[:16], 'score':round(weighted,4), 'dimensions':dims, 'hard_gate':gates, 'prompt_hash':_hash(text), 'decision':'ALLOW' if gates['allow'] and weighted>=0.80 else 'DENY'}

def rank_candidates(candidates:list[dict], fixture:dict|None=None)->dict:
    scored=[score_candidate(c, fixture) for c in candidates]
    scored.sort(key=lambda x:(x['decision']=='ALLOW', x['score']), reverse=True)
    return {'packet_type':'PROMPT_PATCH_RANKING_REPORT_v1','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'candidate_count':len(candidates),'ranked_candidates':scored,'top_candidate':scored[0] if scored else None,'decision':'ALLOW' if scored and scored[0]['decision']=='ALLOW' else 'DENY'}

if __name__=='__main__':
    import sys
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    print(json.dumps(rank_candidates(data.get('candidates',[]), data.get('fixture')), indent=2, sort_keys=True))
