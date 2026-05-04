#!/usr/bin/env python3
import json, sys, hashlib
from pathlib import Path
ROOT=Path('/mnt/data/Metablooms_OS')
STATE=ROOT/'runtime/handoffs/operator_tracker/OPERATOR_VISUAL_TRACKER_STATE_LATEST.json'
HTML=ROOT/'runtime/operator_tracker/operator_visual_tracker_latest.html'
MD=ROOT/'runtime/handoffs/operator_tracker/CURRENT_OPERATOR_TRACKER_PREVIEW_LATEST.md'
CONTRACT=ROOT/'0_kernel/registry/operator_surface/OPERATOR_VISUAL_TRACKER_RENDER_CONTRACT_v1.json'

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576), b''): h.update(b)
 return h.hexdigest()

def fail(msg):
 print(json.dumps({'status':'FAIL','error':msg}, indent=2)); sys.exit(1)
for p in [STATE,HTML,MD,CONTRACT]:
 if not p.exists(): fail(f'missing {p}')
state=json.loads(STATE.read_text(encoding='utf-8'))
contract=json.loads(CONTRACT.read_text(encoding='utf-8'))
html=HTML.read_text(encoding='utf-8')
md=MD.read_text(encoding='utf-8')
for section in contract['required_visual_sections']:
 if f'data-section="{section}"' not in html: fail(f'missing html section {section}')
if '┌' in md or '┏' in md: fail('markdown contains box-drawing status strip')
if md.find('## At a glance') > md.find('## Progress lanes'): fail('markdown visual order invalid')
export=Path(state['latest_export']['path'])
if not export.exists(): fail('latest export path does not exist')
if sha(export) != state['latest_export']['sha256']: fail('latest export sha mismatch')
for needle in ['BOOTABLE OS READY','Progress lanes','Latest bootable export','Decision panel','You are here']:
 if needle not in html and needle not in md: fail(f'missing visible label {needle}')
print(json.dumps({'status':'PASS','html':str(HTML),'markdown':str(MD),'latest_export_sha256':state['latest_export']['sha256']}, indent=2))
