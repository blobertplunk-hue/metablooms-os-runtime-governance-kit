#!/usr/bin/env python3
import json, sys, zipfile
from pathlib import Path
REQ=['Metablooms_OS/0_kernel/scripts/artifact_replay_proof_v2.py','Metablooms_OS/0_kernel/validators/validate_artifact_portability_stage2_v1.py','Metablooms_OS/0_kernel/registry/artifact_portability/MB_ARTIFACT_PORTABILITY_REPLAY_PROOF_SPEC_v2.json','Metablooms_OS/runtime/replay_proof/ARTIFACT_PORTABILITY_REPLAY_PROOF_STAGE2_REPORT_LATEST.json']
def main():
 zpath=Path(sys.argv[1]) if len(sys.argv)>1 else None
 if not zpath or not zpath.exists(): print(json.dumps({'verdict':'FAIL','reason':'archive_missing'})); return 2
 with zipfile.ZipFile(zpath) as z:
  names=z.namelist(); s=set(names); missing=[r for r in REQ if r not in s]; dup=len(names)-len(s); report=json.loads(z.read('Metablooms_OS/runtime/replay_proof/ARTIFACT_PORTABILITY_REPLAY_PROOF_STAGE2_REPORT_LATEST.json'))
 verdict='PASS' if not missing and dup==0 and report.get('verdict')=='REPLAY_PROOF_PASS' else 'FAIL'
 print(json.dumps({'schema_version':'ARTIFACT_PORTABILITY_STAGE2_VALIDATOR_v1','verdict':verdict,'missing_required':missing,'duplicate_entry_count':dup,'report_verdict':report.get('verdict')},indent=2,sort_keys=True)); return 0 if verdict=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
