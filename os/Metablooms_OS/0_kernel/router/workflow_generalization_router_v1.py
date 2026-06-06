#!/usr/bin/env python3
from __future__ import annotations
import json, sys

def route(task_text: str):
    t=(task_text or '').lower()
    cartridges=['NEXT_STAGE_COPY_PROMPT_GENERATOR']
    if any(x in t for x in ['html','student','educational','google sites','staar']):
        cartridges.append('EDUCATIONAL_HTML_DESIGN_SYSTEM_CARTRIDGE')
    if any(x in t for x in ['metrics','dora','observability','baseline']):
        cartridges.append('DORA_STYLE_OS_METRICS_COLLECTOR')
    return {'decision':'ALLOW','cartridges':cartridges,'required_exit_artifacts':['runtime/state/NEXT_STAGE_COPY_PROMPT.md','runtime/state/NEXT_STAGE_COPY_PROMPT.json']}

if __name__ == '__main__':
    print(json.dumps(route(' '.join(sys.argv[1:])), indent=2))
