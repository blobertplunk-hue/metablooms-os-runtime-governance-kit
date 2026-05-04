#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
DEFAULT_IGNORE={'__pycache__','.git','legacy_archives','legacy_quarantine'}
def safe_walk(root, *, ignore_names=None, files_only=True, max_files=None):
    root_path=Path(root); ignore=set(DEFAULT_IGNORE)
    if ignore_names: ignore.update(ignore_names)
    count=0
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in ignore]
        names = filenames if files_only else filenames + dirnames
        for name in names:
            if name in ignore: continue
            p=Path(dirpath)/name
            if files_only and not p.is_file(): continue
            count += 1
            if max_files is not None and count > max_files: raise RuntimeError(f'safe_walk_file_limit_exceeded:{max_files}')
            yield p
