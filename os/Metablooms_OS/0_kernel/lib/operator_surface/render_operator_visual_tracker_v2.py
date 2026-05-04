#!/usr/bin/env python3
from __future__ import annotations
import json, html, argparse
from pathlib import Path

def _esc(x):
    return html.escape(str(x), quote=True)

def _segbar(complete:int, steps:int, active:bool=False):
    parts=[]
    for i in range(steps):
        cls='done' if i < complete else 'empty'
        if active and i == complete:
            cls='active'
        parts.append(f'<span class="seg {cls}"></span>')
    return ''.join(parts)

def render_tracker_html(state:dict)->str:
    h=state['headline']; lanes=state['lanes']; exp=state['latest_export']; dec=state['decisions']
    cards=''.join(f"""<section class="status-card {v.get('status','')}"><div class="status-icon">{_esc(v['icon'])}</div><div><p>{_esc(v['label'])}</p><h2>{_esc(v['summary'])}</h2></div></section>""" for v in h.values())
    lane_html=''.join(f"""<article class="lane"><div class="lane-top"><strong>{_esc(l['name'])}</strong><span class="pill {l['status'].lower()}">{_esc(l['status'])}</span></div><div class="bar">{_segbar(int(l['complete']), int(l['steps']), l['status']=='ACTIVE')}</div></article>""" for l in lanes)
    timeline=''.join(f"""<li class="{_esc(t['state'])}"><span></span>{_esc(t['label'])}</li>""" for t in state.get('timeline',[]))
    opts=''.join(f'<li>{_esc(x)}</li>' for x in dec.get('optional_improvements',[]))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_esc(state.get('title','MetaBlooms Tracker'))}</title>
<style>
:root{{--bg:#0f172a;--panel:#111c33;--panel2:#172442;--text:#eef6ff;--muted:#aab8d4;--green:#22c55e;--blue:#38bdf8;--yellow:#fbbf24;--red:#fb7185;--line:#334155;--shadow:0 14px 34px rgba(0,0,0,.35)}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:linear-gradient(145deg,#0b1020,#111827 48%,#172554);color:var(--text)}}
.wrap{{max-width:1120px;margin:0 auto;padding:18px}} .hero{{display:flex;flex-direction:column;gap:10px;margin:8px 0 16px}} .eyebrow{{color:var(--blue);font-weight:800;letter-spacing:.08em;text-transform:uppercase;font-size:.76rem}} h1{{font-size:clamp(1.6rem,6vw,3.2rem);line-height:1;margin:.05rem 0}} .sub{{color:var(--muted);font-size:1rem;max-width:68ch}}
.status-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}} .status-card{{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid rgba(255,255,255,.10);border-radius:22px;padding:16px;box-shadow:var(--shadow);display:flex;gap:13px;align-items:center;min-height:112px}} .status-icon{{font-size:2.1rem;background:rgba(255,255,255,.08);border-radius:18px;width:58px;height:58px;display:grid;place-items:center}} .status-card p{{margin:0;color:var(--muted);font-weight:700;font-size:.82rem;text-transform:uppercase;letter-spacing:.04em}} .status-card h2{{margin:.25rem 0 0;font-size:1.25rem}} .ready{{border-color:rgba(34,197,94,.5)}} .active{{border-color:rgba(56,189,248,.55)}} .decision{{border-color:rgba(251,191,36,.55)}} .clear{{border-color:rgba(34,197,94,.35)}}
.grid{{display:grid;grid-template-columns:1.25fr .75fr;gap:14px}} .panel{{background:rgba(15,23,42,.82);border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:18px;box-shadow:var(--shadow)}} .panel h3{{margin:.1rem 0 12px;font-size:1.1rem}} .lane{{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:13px;margin:10px 0}} .lane-top{{display:flex;justify-content:space-between;gap:10px;align-items:center}} .pill{{font-size:.72rem;font-weight:900;border-radius:999px;padding:5px 8px;background:#334155;color:#e2e8f0}} .pill.done{{background:rgba(34,197,94,.18);color:#86efac}} .pill.active{{background:rgba(56,189,248,.18);color:#7dd3fc}}
.bar{{display:flex;gap:6px;margin-top:11px}} .seg{{height:15px;flex:1;border-radius:99px;background:#334155}} .seg.done{{background:linear-gradient(90deg,#16a34a,#4ade80)}} .seg.active{{background:linear-gradient(90deg,#0284c7,#7dd3fc)}}
.export-card{{border-left:5px solid var(--green)}} code{{background:rgba(0,0,0,.3);padding:2px 5px;border-radius:6px;word-break:break-all}} .sha{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9rem;color:#dbeafe;word-break:break-all}} .decision-list li{{margin:.45rem 0}} .big-answer{{font-size:1.35rem;font-weight:900;color:#86efac}}
.timeline{{list-style:none;margin:0;padding:0}} .timeline li{{display:flex;align-items:center;gap:10px;margin:12px 0;color:#dbeafe}} .timeline span{{width:14px;height:14px;border-radius:99px;background:#64748b;box-shadow:0 0 0 5px rgba(100,116,139,.14)}} .timeline .done span{{background:var(--green)}} .timeline .active span{{background:var(--blue)}} .timeline .next span{{background:var(--yellow)}}
.receipt{{font-size:.9rem;color:var(--muted);margin-top:16px}} a{{color:#93c5fd}}
@media(max-width:720px){{.wrap{{padding:12px}} .status-grid,.grid{{grid-template-columns:1fr}} .status-card{{min-height:92px;padding:14px;border-radius:18px}} .status-icon{{width:48px;height:48px;font-size:1.7rem}} .panel{{padding:14px;border-radius:18px}}}}
</style></head><body><main class="wrap"><section class="hero"><div class="eyebrow">MetaBlooms OS · Visual Operator Dashboard</div><h1>At-a-glance runtime status</h1><p class="sub">Pre-populated from the current OS handoff. Built to answer: Is there a bootable OS? What are we working on? Is anything blocked? What decision comes next?</p></section><section class="status-grid" data-section="hero_status_cards">{cards}</section><section class="grid"><div class="panel" data-section="progress_lanes"><h3>Progress lanes</h3>{lane_html}</div><aside class="panel export-card" data-section="latest_export_card"><h3>Latest bootable export</h3><p class="big-answer">✅ Available</p><p><strong>Stage:</strong><br>{_esc(exp.get('stage'))}</p><p><strong>SHA:</strong><br><span class="sha">{_esc(exp.get('sha256'))}</span></p><p><strong>Path:</strong><br><code>{_esc(exp.get('path'))}</code></p></aside></section><section class="grid" style="margin-top:14px"><div class="panel" data-section="decision_panel"><h3>Decision panel</h3><p><strong>Safe to stop now:</strong> <span class="big-answer">{_esc(dec.get('safe_to_stop_now'))}</span></p><p><strong>Required blocker:</strong> {_esc(dec.get('required_blocker'))}</p><p><strong>Optional next moves:</strong></p><ul class="decision-list">{opts}</ul><p><strong>Active rule:</strong> {_esc(dec.get('active_rule'))}</p></div><aside class="panel" data-section="timeline"><h3>You are here</h3><ul class="timeline">{timeline}</ul></aside></section><p class="receipt" data-section="compact_technical_receipt">Generated by <code>render_operator_visual_tracker_v2.py</code> from <code>OPERATOR_VISUAL_TRACKER_STATE_LATEST.json</code>.</p></main></body></html>"""

def render_tracker_markdown(state:dict)->str:
    exp=state['latest_export']
    lanes='\n'.join(f"{('✅'*int(l['complete']))}{('▶️' if l['status']=='ACTIVE' else '')}{('□'*(int(l['steps'])-int(l['complete'])-(1 if l['status']=='ACTIVE' and int(l['complete'])<int(l['steps']) else 0)))}  {l['name']}" for l in state['lanes'])
    return f"""# MetaBlooms Operator Tracker\n\n## At a glance\n\n```text\n✅ BOOTABLE OS READY\n🎨 TRACKER HTML POLISH ACTIVE\n⏸️ NEXT WORK: USER DECISION\n```\n\n## Progress lanes\n\n```text\n{lanes}\n```\n\n## Latest full authority\n\n```text\n{exp['path']}\nSHA-256: {exp['sha256']}\n```\n"""

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--state',required=True); ap.add_argument('--html-out',required=True); ap.add_argument('--md-out',required=True); args=ap.parse_args()
    state=json.loads(Path(args.state).read_text(encoding='utf-8'))
    Path(args.html_out).write_text(render_tracker_html(state), encoding='utf-8')
    Path(args.md_out).write_text(render_tracker_markdown(state), encoding='utf-8')
if __name__=='__main__': main()
