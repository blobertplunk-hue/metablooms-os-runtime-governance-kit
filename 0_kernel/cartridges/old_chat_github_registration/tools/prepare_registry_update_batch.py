#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def stamp(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def read(p): return json.loads(Path(p).read_text())
def write(p,d): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def safe_id(s): return ''.join(c if c.isalnum() or c in '-_' else '_' for c in s)[:100]
def counts(chats,items):
    out={k:0 for k in ['finished_verified','finished_unverified','in_progress','blocked','superseded','abandoned','ready_for_promotion','blocked_missing_evidence','blocked_conflict']}
    smap={'COMPLETE_VERIFIED':'finished_verified','COMPLETE_UNVERIFIED':'finished_unverified','IN_PROGRESS':'in_progress','BLOCKED':'blocked','SUPERSEDED':'superseded','ABANDONED':'abandoned'}
    for c in chats:
        if c.get('completion_status') in smap: out[smap[c.get('completion_status')]]+=1
    for i in items:
        if i.get('status')=='READY_FOR_PROMOTION': out['ready_for_promotion']+=1
        if i.get('status')=='BLOCKED_MISSING_LOCAL_EVIDENCE': out['blocked_missing_evidence']+=1
        if i.get('status')=='BLOCKED_PATH_SHA_CONFLICT': out['blocked_conflict']+=1
    return out
def qcounts(items):
    out={k:0 for k in ['ready_for_promotion','blocked_missing_evidence','blocked_conflict','needs_adjudication','do_not_promote']}
    for i in items:
        s=i.get('status')
        if s=='READY_FOR_PROMOTION': out['ready_for_promotion']+=1
        elif s=='BLOCKED_MISSING_LOCAL_EVIDENCE': out['blocked_missing_evidence']+=1
        elif s=='BLOCKED_PATH_SHA_CONFLICT': out['blocked_conflict']+=1
        elif s=='NEEDS_HUMAN_ADJUDICATION': out['needs_adjudication']+=1
        elif s in ['SMOKE_ONLY_DO_NOT_PROMOTE','SUPERSEDED_DO_NOT_PROMOTE']: out['do_not_promote']+=1
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--packet',required=True); ap.add_argument('--report',required=True); ap.add_argument('--registry',required=True); ap.add_argument('--queue',required=True); ap.add_argument('--out-dir',required=True); a=ap.parse_args()
    packet,report,reg,queue=read(a.packet),read(a.report),read(a.registry),read(a.queue)
    sid=safe_id(packet['source_chat_id']); ppath=f'governance/chat_work_registry/chat_packets/{sid}.json'; rpath=f'governance/chat_work_registry/reports/{sid}.comparison_report.json'
    if any(c.get('chat_url')==packet['chat_url'] and c.get('source_chat_id')!=packet['source_chat_id'] for c in reg['chats']): raise SystemExit('duplicate chat_url conflict')
    ready=sum(1 for x in report.get('unshared',[]) if x.get('local_evidence_path'))
    row={'chat_url':packet['chat_url'],'source_chat_id':packet['source_chat_id'],'registered_at_utc':packet.get('registered_at_utc',stamp()),'last_seen_at_utc':stamp(),'work_summary':packet.get('work_summary',''),'completion_status':packet.get('completion_status','COMPLETE_UNVERIFIED'),'done_count':len(packet.get('done_work',[])),'unfinished_count':len(packet.get('current_work',[])),'blocked_count':len(packet.get('blockers',[])),'ready_for_promotion_count':ready,'packet_path':ppath,'report_path':rpath}
    reg['chats']=[c for c in reg['chats'] if c.get('source_chat_id')!=packet['source_chat_id']]+[row]
    keys={i.get('key') for i in queue['items']}
    for x in report.get('unshared',[]):
        key=sid+'|'+str(x.get('declared_path'))+'|'+str(x.get('sha256'))
        if key not in keys:
            queue['items'].append({'key':key,'chat_url':packet['chat_url'],'source_chat_id':packet['source_chat_id'],'label':x.get('label',''),'declared_path':x.get('declared_path'),'sha256':x.get('sha256'),'status':'READY_FOR_PROMOTION' if x.get('local_evidence_path') else 'BLOCKED_MISSING_LOCAL_EVIDENCE','created_at_utc':stamp(),'packet_path':ppath,'report_path':rpath})
    for x in report.get('conflicts',[]):
        key=sid+'|conflict|'+str(x.get('declared_path'))+'|'+str(x.get('sha256'))
        if key not in keys:
            queue['items'].append({'key':key,'chat_url':packet['chat_url'],'source_chat_id':packet['source_chat_id'],'label':x.get('label',''),'declared_path':x.get('declared_path'),'sha256':x.get('sha256'),'status':'BLOCKED_PATH_SHA_CONFLICT','created_at_utc':stamp(),'packet_path':ppath,'report_path':rpath})
    reg['registered_chat_count']=len(reg['chats']); reg['queue_counts']=counts(reg['chats'],queue['items']); reg['updated_at_utc']=stamp(); queue['queue_item_count']=len(queue['items']); queue['status_counts']=qcounts(queue['items']); queue['updated_at_utc']=stamp()
    out=Path(a.out_dir); write(out/'governance/chat_work_registry/registered_chats.index.json',reg); write(out/'governance/chat_work_registry/promotion_queue.index.json',queue); write(out/ppath,packet); write(out/rpath,report); write(out/'registry_update_receipt.json',{'decision':'PASS_PREPARED_REGISTRY_UPDATE','packet_path':ppath,'report_path':rpath,'registered_chat_count':len(reg['chats']),'queue_item_count':len(queue['items'])})
if __name__=='__main__': main()
