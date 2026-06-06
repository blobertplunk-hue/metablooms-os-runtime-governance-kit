# Python Sandbox Findings

## Summary
- `python3 -V` is fast (~0.05s).
- `python3 -c 'print("ok")'` is slow (~3.0s) and high-memory (~270MB).
- `python3 -S -c 'print("ok")'` is fast (~0.07-0.09s) and low-memory (~14MB).
- `-E`, `-I`, and `-s` do **not** fix the slowdown.
- The slowdown is therefore in standard `site` startup hooks, not normal interpreter startup and not ordinary environment-variable or user-site handling.

## Proven startup chain
- `.pth`: `/opt/pyvenv/lib/python3.13/site-packages/000_oai_py_sys_path_prepend.pth`
- module: `oai_py_sys_path_prepend`
- injected paths: `/opt/python-hooks`, `/opt/pyvenv-libs`, `/opt/pyvenv-overrides`
- `sitecustomize`: `/opt/python-hooks/sitecustomize.py`
- `sitecustomize` imports `presentation_artifact_tool` and `presentation_artifact_tool.patches.record_artifact_tool_operations`

## Import-time evidence
- `oai_py_sys_path_prepend`: ~2.7 ms self time
- `presentation_artifact_tool`: ~839.6 ms cumulative
- `presentation_artifact_tool.generated.interface.models`: ~686.5 ms cumulative
- `presentation_artifact_tool.rpc.types`: ~362.8 ms cumulative
- `sitecustomize`: ~2758.9 ms cumulative

## Root-cause class
Python startup is being slowed by a forced `site` initialization chain that injects OpenAI-specific hook paths via `.pth`, then executes `sitecustomize`, which eagerly imports `presentation_artifact_tool` and associated RPC/model modules.
