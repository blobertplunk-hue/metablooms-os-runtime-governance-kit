#!/usr/bin/env python3
import json, pathlib, sys, time, hashlib, os

def sha(path):
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name+'.sha256').write_text(f'{h}  {path.name}\n', encoding='utf-8')
    return h

def emit(root, stage, previous_stage, authority, steps, current_step=0, status='active'):
    root=pathlib.Path(root)
    state=root/'runtime/state'
    state.mkdir(parents=True, exist_ok=True)
    data={
        'schema_version':'v1',
        'generated_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'stage':stage,
        'previous_stage':previous_stage,
        'primary_authority':authority,
        'status':status,
        'current_step':current_step,
        'steps':steps,
        'next_prompt_required':True,
        'export_required':True,
        'download_link_precheck_required':True,
    }
    json_path=state/'ACTIVE_PROCESS_TRACKER_PREVIEW.json'
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
    sha(json_path)
    lines=[]
    lines.append('MetaBlooms governed process tracker')
    lines.append(f'Stage: {stage}')
    lines.append(f'Previous: {previous_stage}')
    lines.append(f'Status: {status}')
    lines.append(f'Authority: {authority}')
    for i, step in enumerate(steps, start=1):
        mark='▶' if i==current_step else ('✓' if i<current_step else '•')
        lines.append(f'{mark} {i}. {step}')
    lines.append('Exit gates: receipt + handoff + next prompt + short full-authority export + link precheck')
    txt_path=state/'ACTIVE_PROCESS_TRACKER_PREVIEW.txt'
    txt_path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    sha(txt_path)
    return data

if __name__ == '__main__':
    root=sys.argv[1] if len(sys.argv)>1 else '/mnt/data/Metablooms_OS'
    stage=sys.argv[2] if len(sys.argv)>2 else 'UNKNOWN_STAGE'
    previous=sys.argv[3] if len(sys.argv)>3 else 'UNKNOWN_PREVIOUS_STAGE'
    authority=sys.argv[4] if len(sys.argv)>4 else 'UNKNOWN_AUTHORITY'
    steps=['boot','load authorities','run bounded stage','verify','export','link precheck']
    data=emit(root, stage, previous, authority, steps, current_step=6, status='ready')
    print(json.dumps(data, indent=2))
