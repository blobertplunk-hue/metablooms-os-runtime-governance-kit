#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json, time
from pathlib import Path

STAGE_ID='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE3_TRACKER_CAUSAL_TIMELINE_BINDING'

def utc_now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def sha_file(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*512), b''): h.update(c)
    return h.hexdigest()
def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text=json.dumps(obj, indent=2, sort_keys=True)+'\n'
    path.write_text(text, encoding='utf-8')
    (path.with_suffix(path.suffix+'.sha256')).write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+path.name+'\n', encoding='utf-8')
def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    (path.with_suffix(path.suffix+'.sha256')).write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+path.name+'\n', encoding='utf-8')
def load(path: Path): return json.loads(path.read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x), quote=True)
def status_class(s):
    s=(s or '').upper()
    if s=='OK': return 'ok'
    if s=='WARN': return 'warn'
    if s=='BLOCKED': return 'blocked'
    if s=='ERROR': return 'error'
    return 'neutral'
def shorten_stage(stage: str, n=50):
    if not stage: return 'Unknown stage'
    return stage if len(stage)<=n else stage[:n-1]+'…'

def latest_export(root: Path):
    zips=sorted(root.parent.glob('METABLOOMS_OS_*zip'), key=lambda p:p.stat().st_mtime, reverse=True)
    if not zips:
        return {'available': False, 'path': None, 'sha256': None, 'stage': None}
    z=zips[0]
    side=Path(str(z)+'.sha256')
    sha=side.read_text().split()[0] if side.exists() else sha_file(z)
    return {'available': True, 'path': str(z), 'sha256': sha, 'stage': z.stem.replace('METABLOOMS_OS_','')}

def build_timeline_model(root: Path):
    index_path=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json'
    graph_path=root/'runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json'
    ledger_path=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl'
    index=load(index_path); graph=load(graph_path)
    ledger_records=[]
    for line in ledger_path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            ledger_records.append(json.loads(line))
    latest=sorted(ledger_records, key=lambda r: str(r.get('timestamp_utc','')))[-12:]
    issue_records=[r for r in ledger_records if r.get('status') in ('BLOCKED','ERROR','WARN')]
    current=latest[-1] if latest else {}
    blockers=[r for r in latest if r.get('status') in ('BLOCKED','ERROR')]
    blocker=blockers[-1] if blockers else None
    next_action = 'Proceed with next governed user-selected stage.'
    if blocker:
        next_action = 'Resolve latest blocker before execution resumes.'
    elif current.get('event_kind') == 'handoff':
        next_action = 'Use the latest handoff as the next-stage starting point.'
    model={
        'artifact_type':'MB_OPERATOR_CAUSAL_TIMELINE.v1',
        'stage_id':STAGE_ID,
        'created_utc':utc_now(),
        'source_inputs': {
            'trace_index': str(index_path.relative_to(root)),
            'causal_graph': str(graph_path.relative_to(root)),
            'trace_ledger': str(ledger_path.relative_to(root)),
            'trace_index_sha256': sha_file(index_path),
            'causal_graph_sha256': sha_file(graph_path),
            'trace_ledger_sha256': sha_file(ledger_path)
        },
        'summary': {
            'record_count': index.get('record_count'),
            'graph_node_count': graph.get('summary',{}).get('node_count'),
            'graph_edge_count': graph.get('summary',{}).get('edge_count'),
            'ok_count': index.get('by_status',{}).get('OK',0),
            'warn_count': index.get('by_status',{}).get('WARN',0),
            'blocked_count': index.get('by_status',{}).get('BLOCKED',0),
            'error_count': index.get('by_status',{}).get('ERROR',0),
            'event_kinds': index.get('by_kind',{})
        },
        'current_state': {
            'latest_event': current,
            'latest_blocker': blocker,
            'issue_record_count': len(issue_records),
            'next_action': next_action,
            'safe_to_continue': blocker is None
        },
        'timeline': [{k:r.get(k) for k in ['timestamp_utc','event_name','stage_id','event_kind','status','source_artifact','span_id','parent_span_id']} for r in latest],
        'issue_records': [{k:r.get(k) for k in ['timestamp_utc','event_name','stage_id','status','source_artifact','span_id']} for r in issue_records[-10:]],
        'latest_export': latest_export(root)
    }
    return model

def render_html(model):
    s=model['summary']; cur=model['current_state']; latest=cur.get('latest_event') or {}; blocker=cur.get('latest_blocker')
    exp=model['latest_export']
    cards=[
        ('Trace records', s.get('record_count'), 'ok'),
        ('Graph nodes', s.get('graph_node_count'), 'ok'),
        ('Known blockers', s.get('blocked_count',0)+s.get('error_count',0), 'blocked' if s.get('blocked_count',0)+s.get('error_count',0) else 'ok'),
        ('Safe to continue', 'Yes' if cur.get('safe_to_continue') else 'No', 'ok' if cur.get('safe_to_continue') else 'blocked')
    ]
    card_html=''.join(f'<section class="metric {cls}"><div class="metric-label">{esc(label)}</div><div class="metric-value">{esc(value)}</div></section>' for label,value,cls in cards)
    kind_html=''.join(f'<span class="chip">{esc(k)} <b>{esc(v)}</b></span>' for k,v in sorted(s.get('event_kinds',{}).items()))
    rows=[]
    for r in model['timeline']:
        cls=status_class(r.get('status'))
        rows.append(f'''<article class="span-row {cls}">
          <div class="dot"></div><div class="span-main"><div class="span-title">{esc(r.get('event_name'))}</div>
          <div class="span-meta">{esc(r.get('timestamp_utc'))} · {esc(shorten_stage(r.get('stage_id',''),72))}</div>
          <div class="span-source">Evidence: <code>{esc(r.get('source_artifact'))}</code></div></div>
          <div class="span-status">{esc(r.get('status'))}</div>
        </article>''')
    blocker_html = '<p class="oktext">No active blocker in the latest trace window.</p>' if not blocker else f'<p class="badtext">{esc(blocker.get("status"))}: {esc(shorten_stage(blocker.get("stage_id",""),90))}</p><p><code>{esc(blocker.get("source_artifact"))}</code></p>'
    issue_html=''.join(f'<li><b>{esc(r.get("status"))}</b> · {esc(shorten_stage(r.get("stage_id",""),80))}<br><code>{esc(r.get("source_artifact"))}</code></li>' for r in model.get('issue_records',[])) or '<li>No issue records found.</li>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MetaBlooms Operator Causal Tracker</title>
<style>
:root{{--bg:#0b1020;--panel:#101b33;--panel2:#17213f;--line:#30415f;--text:#eef6ff;--muted:#aec0dc;--ok:#22c55e;--warn:#fbbf24;--bad:#fb7185;--blue:#38bdf8;--shadow:0 16px 34px rgba(0,0,0,.34)}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at top left,#1e3a8a 0,#0b1020 36%,#111827 100%);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}} .wrap{{max-width:1160px;margin:0 auto;padding:16px}} .hero{{padding:18px 0 8px}} .eyebrow{{color:var(--blue);font-weight:900;letter-spacing:.08em;text-transform:uppercase;font-size:.75rem}} h1{{font-size:clamp(1.75rem,7vw,3.4rem);line-height:.96;margin:.25rem 0}} .sub{{color:var(--muted);max-width:72ch;margin:0;font-size:1rem}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}} .metric{{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid rgba(255,255,255,.12);border-radius:22px;padding:15px;box-shadow:var(--shadow)}} .metric-label{{font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:800}} .metric-value{{font-size:1.65rem;font-weight:950;margin-top:4px}} .metric.ok{{border-color:rgba(34,197,94,.48)}} .metric.blocked{{border-color:rgba(251,113,133,.65)}}
.grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:14px}} .panel{{background:rgba(15,23,42,.84);border:1px solid rgba(255,255,255,.11);border-radius:24px;padding:16px;box-shadow:var(--shadow)}} h2{{font-size:1.12rem;margin:.1rem 0 12px}} .chips{{display:flex;flex-wrap:wrap;gap:8px}} .chip{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.10);border-radius:999px;padding:7px 10px;color:#dbeafe;font-size:.86rem}} .chip b{{color:#fff}}
.span-row{{display:grid;grid-template-columns:20px 1fr auto;gap:10px;align-items:center;padding:12px;margin:9px 0;border-radius:18px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.08)}} .dot{{width:14px;height:14px;border-radius:50%;background:#64748b;box-shadow:0 0 0 5px rgba(100,116,139,.15)}} .span-row.ok .dot{{background:var(--ok);box-shadow:0 0 0 5px rgba(34,197,94,.15)}} .span-row.warn .dot{{background:var(--warn);box-shadow:0 0 0 5px rgba(251,191,36,.15)}} .span-row.blocked .dot,.span-row.error .dot{{background:var(--bad);box-shadow:0 0 0 5px rgba(251,113,133,.15)}} .span-title{{font-weight:900}} .span-meta,.span-source{{color:var(--muted);font-size:.86rem;margin-top:3px}} .span-status{{font-weight:950;font-size:.75rem;border-radius:999px;background:#334155;padding:6px 8px}} code{{background:rgba(0,0,0,.28);border-radius:6px;padding:2px 5px;word-break:break-all}} .next{{border-left:6px solid var(--blue)}} .oktext{{color:#86efac;font-weight:900}} .badtext{{color:#fda4af;font-weight:900}} .evidence li{{margin:9px 0;color:#dbeafe}} .footer{{color:var(--muted);font-size:.86rem;margin:16px 2px}}
@media(max-width:760px){{.wrap{{padding:12px}} .metrics,.grid{{grid-template-columns:1fr}} .metric{{border-radius:18px}} .panel{{border-radius:18px;padding:14px}} .span-row{{grid-template-columns:18px 1fr;align-items:start}} .span-status{{grid-column:2;justify-self:start}}}}
</style></head><body><main class="wrap"><section class="hero"><div class="eyebrow">MetaBlooms OS · Causal Operator Tracker</div><h1>Cause → evidence → next action</h1><p class="sub">This dashboard is pre-populated from the trace/span ledger and causal graph. It is designed to show the current state visually without requiring raw receipt reading.</p></section>
<section class="metrics" data-section="hero_status_cards" aria-label="Runtime summary cards">{card_html}</section>
<section class="grid"><section class="panel" data-section="causal_timeline"><h2>Causal timeline · latest trace window</h2>{''.join(rows)}</section><aside class="panel next" data-section="next_action_card"><h2>Next action</h2><p class="oktext">{esc(cur.get('next_action'))}</p><h2>Current blocker</h2>{blocker_html}<h2>Latest event</h2><p><b>{esc(latest.get('status'))}</b> · {esc(latest.get('event_name'))}</p><p><code>{esc(latest.get('source_artifact'))}</code></p></aside></section>
<section class="grid" style="margin-top:14px"><section class="panel" data-section="causal_summary_cards"><h2>Event type mix</h2><div class="chips">{kind_html}</div><h2 style="margin-top:18px">Latest bootable export</h2><p><b>{'Available' if exp.get('available') else 'Not found'}</b></p><p><code>{esc(exp.get('path'))}</code></p><p><code>{esc(exp.get('sha256'))}</code></p></section><aside class="panel" data-section="evidence_strip"><h2>Issue evidence strip</h2><ul class="evidence">{issue_html}</ul></aside></section><p class="footer">Generated by <code>build_operator_tracker_causal_timeline_v1.py</code> from <code>OPERATOR_CAUSAL_TIMELINE_LATEST.json</code>. Stage: <code>{STAGE_ID}</code>. Created: {esc(model.get('created_utc'))}.</p></main></body></html>'''

def render_preview(model):
    s=model['summary']; cur=model['current_state']
    lines=[
        '# MetaBlooms Operator Causal Timeline', '',
        f"Records: {s.get('record_count')} | Nodes: {s.get('graph_node_count')} | Edges: {s.get('graph_edge_count')}",
        f"OK: {s.get('ok_count')} | WARN: {s.get('warn_count')} | BLOCKED: {s.get('blocked_count')} | ERROR: {s.get('error_count')}",
        f"Safe to continue: {cur.get('safe_to_continue')}",
        f"Next action: {cur.get('next_action')}", '', '## Latest trace window'
    ]
    for r in model['timeline']:
        lines.append(f"- {r.get('status')} · {r.get('event_name')} · {r.get('stage_id')} · {r.get('source_artifact')}")
    return '\n'.join(lines)+'\n'

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true')
    args=ap.parse_args(argv); root=Path(args.root).resolve()
    model=build_timeline_model(root)
    model_path=root/'runtime/state/operator_surface/OPERATOR_CAUSAL_TIMELINE_LATEST.json'
    html_path=root/'OPEN_OPERATOR_VISUAL_TRACKER.html'
    preview_path=root/'runtime/state/operator_surface/OPERATOR_CAUSAL_TIMELINE_PREVIEW_LATEST.md'
    write_json(model_path, model)
    write_text(preview_path, render_preview(model))
    write_text(html_path, render_html(model))
    report={'artifact_type':'MB_OPERATOR_TRACKER_CAUSAL_TIMELINE_BUILD_REPORT.v1','stage_id':STAGE_ID,'created_utc':utc_now(),'verdict':'PASS','outputs':[str(model_path.relative_to(root)),str(preview_path.relative_to(root)),str(html_path.relative_to(root))], 'model_summary': model['summary']}
    out=root/'runtime/state/operator_surface/OPERATOR_CAUSAL_TIMELINE_BUILD_REPORT_LATEST.json'
    write_json(out, report)
    if args.json: print(json.dumps(report, indent=2, sort_keys=True))
if __name__=='__main__': main()
