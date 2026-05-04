#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[2]
required=[
 'tools/metablooms/termux/metablooms',
 'tools/metablooms/termux/install-metablooms-operator.sh',
 'governance/operator_ux/OPERATOR_COMMAND_IMPLEMENTATION_SPEC_v1.json',
 'governance/operator_ux/STAGE43B0_IMPLEMENTATION_NOTES.md'
]
for rel in required:
    p=root/rel
    assert p.exists(), f'missing {rel}'
text=(root/'tools/metablooms/termux/metablooms').read_text()
for cmd in ['status_cmd','merge_pr_cmd','copyback','relax_rulesets','restore_rulesets']:
    assert cmd in text, f'missing function {cmd}'
print('PASS: operator UX abstraction layer present')
