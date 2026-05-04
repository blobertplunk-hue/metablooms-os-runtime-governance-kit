#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,collections
from pathlib import Path
def toks(s): return re.findall(r"[a-z0-9_./:-]{2,}",s.lower())
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--query",default="export proof sha256"); ap.add_argument("--json",action="store_true"); a=ap.parse_args(); root=Path(a.root); idx=json.loads((root/"runtime/traces/observability/SEARCHABLE_EVIDENCE_INDEX_LATEST.json").read_text()); scores=collections.Counter(); hits=collections.defaultdict(list)
 for t in toks(a.query):
  for p in idx.get("inverted_index",{}).get(t,[]): scores[p["doc_id"]]+=p.get("tf",1); hits[p["doc_id"]].append(t)
 by={d["doc_id"]:d for d in idx.get("documents",[])}; res=[]
 for did,score in scores.most_common(10):
  d=by[did]; res.append({"doc_id":did,"score":score,"path":d["path"],"matched_terms":sorted(set(hits[did]))})
 print(json.dumps({"artifact_type":"MB_TRACE_QUERY_RESULT.v1","verdict":"PASS" if res else "FAIL","query":a.query,"results":res},indent=2,sort_keys=True)); return 0 if res else 2
if __name__=="__main__": raise SystemExit(main())
