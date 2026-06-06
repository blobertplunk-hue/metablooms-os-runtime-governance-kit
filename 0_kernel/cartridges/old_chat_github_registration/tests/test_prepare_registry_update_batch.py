from __future__ import annotations
import json, subprocess, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools/prepare_registry_update_batch.py'
def h(x): return hashlib.sha256(x.encode()).hexdigest()
def base(tmp):
    reg={'schema':'mb.old_chat_github_registration.github_registry_index.v1','updated_at_utc':'2026-06-05T00:00:00Z','repo':'blobertplunk-hue/metablooms-os-runtime-governance-kit','registered_chat_count':0,'queue_counts':{'finished_verified':0,'finished_unverified':0,'in_progress':0,'blocked':0,'superseded':0,'abandoned':0,'ready_for_promotion':0,'blocked_missing_evidence':0,'blocked_conflict':0},'chats':[]}
    q={'schema':'mb.old_chat_github_registration.github_promotion_queue_index.v1','updated_at_utc':'2026-06-05T00:00:00Z','repo':'blobertplunk-hue/metablooms-os-runtime-governance-kit','queue_item_count':0,'status_counts':{'ready_for_promotion':0,'blocked_missing_evidence':0,'blocked_conflict':0,'needs_adjudication':0,'do_not_promote':0},'items':[]}
    (tmp/'reg.json').write_text(json.dumps(reg)); (tmp/'q.json').write_text(json.dumps(q))
def packet():
    return {'schema':'mb.old_chat_github_registration.work_status_packet.v1','chat_url':'https://chatgpt.com/c/stage-v','source_chat_id':'stage-v','registered_at_utc':'2026-06-05T00:00:00Z','work_summary':'Stage V smoke','completion_status':'COMPLETE_UNVERIFIED','done_work':[{'label':'done','description':'done'}],'current_work':[],'blockers':[],'artifacts':[],'next_actions':['review']}
def report():
    return {'schema':'mb.old_chat_github_registration.report.v1','chat_url':'https://chatgpt.com/c/stage-v','source_chat_id':'stage-v','unshared':[{'label':'ready','declared_path':'x.md','sha256':h('x'),'local_evidence_path':'/tmp/x.md'},{'label':'blocked','declared_path':'y.md','sha256':h('y')}],'conflicts':[],'missing_local_evidence':[],'artifacts':[],'decision':'PASS_COMPARE_COMPLETE'}
def test_prepare_registry_update_batch(tmp_path: Path):
    base(tmp_path); (tmp_path/'packet.json').write_text(json.dumps(packet())); (tmp_path/'report.json').write_text(json.dumps(report())); out=tmp_path/'out'
    subprocess.run(['python3',str(TOOL),'--packet',str(tmp_path/'packet.json'),'--report',str(tmp_path/'report.json'),'--registry',str(tmp_path/'reg.json'),'--queue',str(tmp_path/'q.json'),'--out-dir',str(out)],check=True)
    reg=json.loads((out/'governance/chat_work_registry/registered_chats.index.json').read_text()); q=json.loads((out/'governance/chat_work_registry/promotion_queue.index.json').read_text())
    assert reg['registered_chat_count']==1
    assert q['queue_item_count']==2
    assert q['status_counts']['ready_for_promotion']==1
    assert q['status_counts']['blocked_missing_evidence']==1
    assert (out/'governance/chat_work_registry/chat_packets/stage-v.json').exists()
    assert (out/'governance/chat_work_registry/reports/stage-v.comparison_report.json').exists()
