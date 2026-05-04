#!/usr/bin/env python3
from __future__ import annotations
import json, sys, hashlib, zipfile
from pathlib import Path
ROOT=Path('/mnt/data/Metablooms_OS')
HTML=ROOT/'OPEN_OPERATOR_VISUAL_TRACKER.html'
RUNTIME_HTML=ROOT/'runtime/operator_tracker/operator_visual_tracker_latest.html'
MANIFEST=ROOT/'runtime/operator_tracker/OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_LATEST.json'
NEWCHAT=ROOT/'NEW_CHAT_START_HERE.md'
STATE=ROOT/'runtime/handoffs/operator_tracker/OPERATOR_VISUAL_TRACKER_STATE_LATEST.json'
CONTRACT=ROOT/'0_kernel/registry/operator_surface/OPERATOR_VISUAL_TRACKER_RENDER_CONTRACT_v1.json'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def fail(msg):
    print(json.dumps({'status':'FAIL','error':msg}, indent=2)); sys.exit(1)
for p in [HTML,RUNTIME_HTML,MANIFEST,NEWCHAT,STATE,CONTRACT]:
    if not p.exists(): fail(f'missing {p}')
if sha(HTML) != sha(RUNTIME_HTML): fail('root html and runtime html mismatch')
html=HTML.read_text(encoding='utf-8')
for needle in ['data-section="hero_status_cards"','data-section="progress_lanes"','data-section="latest_export_card"','data-section="decision_panel"','data-section="timeline"']:
    if needle not in html: fail(f'missing visual section {needle}')
newchat=NEWCHAT.read_text(encoding='utf-8')
for needle in ['OPEN_OPERATOR_VISUAL_TRACKER.html','operator_visual_tracker_latest.html','OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_LATEST.json']:
    if needle not in newchat: fail(f'NEW_CHAT_START_HERE missing {needle}')
manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
if manifest.get('final_export_binding',{}).get('external_sidecar_required') is not True: fail('missing external sidecar self-hash rule')
state=json.loads(STATE.read_text(encoding='utf-8'))
if state.get('stage3_boot_surface_binding',{}).get('root_html') != 'OPEN_OPERATOR_VISUAL_TRACKER.html': fail('state missing root html binding')
print(json.dumps({'status':'PASS','root_html':str(HTML),'runtime_html':str(RUNTIME_HTML),'manifest':str(MANIFEST),'root_html_sha256':sha(HTML)}, indent=2))
