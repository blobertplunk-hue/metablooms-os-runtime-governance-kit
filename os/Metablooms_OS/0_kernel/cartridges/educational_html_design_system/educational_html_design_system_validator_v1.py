#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, re, sys

def validate_html(path: Path):
    s=path.read_text(encoding='utf-8')
    checks={
      'doctype':'<!doctype html' in s.lower(),
      'lang':'<html' in s.lower() and ' lang=' in s.lower(),
      'viewport':'name="viewport"' in s.lower() or "name='viewport'" in s.lower(),
      'tokens':'--mb-color-bg' in s and '--mb-touch-target-min' in s,
      'aria_live':'aria-live' in s,
      'focus_style':':focus' in s or ':focus-visible' in s,
      'no_cdn':'https://cdn' not in s.lower() and 'unpkg.com' not in s.lower(),
      'reduced_motion':'prefers-reduced-motion' in s
    }
    return {'decision':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'path':str(path)}
if __name__=='__main__': print(json.dumps(validate_html(Path(sys.argv[1])), indent=2))
