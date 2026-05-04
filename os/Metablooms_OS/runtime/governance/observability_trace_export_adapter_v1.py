#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, sys
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def stable_id(prefix, obj): return prefix+'_'+h(json.dumps(obj, sort_keys=True, default=str))[:16]

def normalize(packet):
    stage=packet.get('stage_id') or packet.get('stage') or 'UNKNOWN_STAGE'
    name=packet.get('name') or packet.get('event') or packet.get('action_type') or 'metablooms.action'
    attrs=dict(packet.get('attributes') or {})
    for k in ['tool_id','tool_name','action_type','risk_tier','policy_decision','approval_token_id','checkpoint_id','thread_id','bts_commit_id']:
        if k in packet and k not in attrs: attrs[k]=packet[k]
    status=packet.get('status') or packet.get('decision') or 'UNSET'
    trace_id=packet.get('trace_id') or stable_id('trace', {'stage':stage,'thread':attrs.get('thread_id'),'root':packet.get('root_stage_id') or stage})
    span_id=packet.get('span_id') or stable_id('span', packet)
    parent=packet.get('parent_span_id') or packet.get('parent_run_id') or None
    ts=packet.get('timestamp_utc') or packet.get('created_at_utc') or now()
    return {'schema':'MetaBloomsTraceSpan_v1','trace_id':trace_id,'span_id':span_id,'parent_span_id':parent,'stage_id':stage,'name':name,'kind':packet.get('kind','INTERNAL'),'timestamp_utc':ts,'attributes':attrs,'events':packet.get('events',[]),'links':packet.get('links',[]),'status':status}

def to_otel(span):
    attrs=[{'key':k,'value':v} for k,v in sorted((span.get('attributes') or {}).items())]
    return {'traceId':span['trace_id'],'spanId':span['span_id'],'parentSpanId':span.get('parent_span_id'),'name':span['name'],'kind':span.get('kind','INTERNAL'),'startTimeUnixNano':span.get('start_time_unix_nano',0),'endTimeUnixNano':span.get('end_time_unix_nano',0),'attributes':attrs,'events':span.get('events',[]),'links':span.get('links',[]),'status':{'code':span.get('status','UNSET')}}

def to_agents(span):
    return {'type':'metablooms.trace_event','trace_id':span['trace_id'],'span_id':span['span_id'],'parent_span_id':span.get('parent_span_id'),'stage_id':span['stage_id'],'event':span['name'],'attributes':span.get('attributes',{}),'status':span.get('status')}

def to_langgraph(span):
    a=span.get('attributes') or {}
    return {'run_id':span['span_id'],'parent_run_id':span.get('parent_span_id'),'thread_id':a.get('thread_id'),'checkpoint_id':a.get('checkpoint_id'),'name':span['name'],'inputs':{},'outputs':{},'metadata':{'stage_id':span['stage_id'],'trace_id':span['trace_id'],'status':span.get('status'),'attributes':a}}

def validate_span(span):
    missing=[k for k in ['trace_id','span_id','stage_id','name','status'] if not span.get(k)]
    attrs=span.get('attributes') or {}
    if attrs.get('risk_tier') in {'high','critical'}:
        for k in ['tool_id','action_type','policy_decision']:
            if not attrs.get(k): missing.append('security_attribute:'+k)
    return {'decision':'ALLOW' if not missing else 'DENY','missing':missing}

def main(argv=None):
    argv=argv or sys.argv[1:]
    if len(argv)<3: raise SystemExit('usage: observability_trace_export_adapter_v1.py <input.json> <format> <output.json>')
    packet=load(argv[0]); fmt=argv[1]; out=Path(argv[2])
    span=normalize(packet); val=validate_span(span)
    if val['decision']!='ALLOW':
        result={'schema':'TraceExportAdapterResult_v1','decision':'DENY','errors':val['missing'],'span':span}
    else:
        exporters={'metablooms_jsonl':span,'opentelemetry_span_json':to_otel(span),'openai_agents_event_json':to_agents(span),'langgraph_run_json':to_langgraph(span)}
        if fmt not in exporters: raise SystemExit('unsupported format '+fmt)
        result={'schema':'TraceExportAdapterResult_v1','decision':'ALLOW','format':fmt,'record':exporters[fmt],'span':span}
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['decision']=='ALLOW' else 20
if __name__=='__main__': raise SystemExit(main())
