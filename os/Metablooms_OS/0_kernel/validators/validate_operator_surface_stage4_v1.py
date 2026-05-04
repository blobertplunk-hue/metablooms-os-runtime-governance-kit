#!/usr/bin/env python3
from pathlib import Path
import json
def root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def main():
 r=root(); req=['bin/mb','0_kernel/scripts/stage_runner_v1.py','0_kernel/scripts/cartridge_executor_v1.py','0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v4.json','0_kernel/registry/operator_surface/MB_CARTRIDGE_EXECUTOR_CONTRACT_v1.json','0_kernel/registry/operator_surface/MB_OBSERVABILITY_TRACE_LEDGER_SPEC_v1.json','0_kernel/registry/operator_surface/CARTRIDGE_EXECUTOR_REGISTRY_v1.json','0_kernel/validators/validate_operator_surface_stage4_v1.py','docs/operator_surface/MB_OPERATOR_QUICKSTART_v4.md','runtime/receipts/external_review/UX_OPERATOR_SURFACE_STAGE_4_RECEIPT_LATEST.json','runtime/handoffs/external_review/UX_OPERATOR_SURFACE_STAGE_4_HANDOFF_LATEST.json']
 checks={x:(r/x).exists() for x in req}; verdict='PASS' if all(checks.values()) else 'FAIL'; print(json.dumps({'artifact_type':'OPERATOR_SURFACE_STAGE4_VALIDATION_v1','verdict':verdict,'root':str(r),'checks':checks},indent=2,sort_keys=True)); return 0 if verdict=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
