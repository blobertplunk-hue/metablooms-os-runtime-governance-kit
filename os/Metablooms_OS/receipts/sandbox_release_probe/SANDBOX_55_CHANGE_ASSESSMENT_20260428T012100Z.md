# Sandbox 5.5-era Change Assessment

## Scope
Current sandbox fingerprint plus official GPT-5.5 release material.

## Strong findings
- GPT-5.5 official material emphasizes stronger agentic tool use, document/spreadsheet work, and moving across tools.
- The current sandbox has Python startup hook injection through `.pth` -> `oai_py_sys_path_prepend` -> `/opt/python-hooks/sitecustomize.py`.
- The current startup hook eagerly imports `presentation_artifact_tool` and its operation-recording patch.
- The path-prepend files were installed on 2026-04-21.
- The `presentation_artifact_tool` package directory has mtime 2026-04-21 21:29:17 UTC.
- `/opt/python-hooks/sitecustomize.py` has mtime 2026-04-28 01:13:18 UTC, indicating a very recent edit after GPT-5.5 release day.
- Environment flags present now include:
  - `CUA_DD_INIT_ARTIFACT_TOOL_V2=true`
  - `CUA_DD_INIT_ARTIFACT_TOOL_V2_RECORD_OPERATIONS=true`
  - `CUA_DD_PYTHON_TOOL=true`
  - `CUA_DD_PYTHON_TOOL_WARM_SPREADSHEET_RUNTIME=true`

## Conservative inference
These findings support that the sandbox/tooling stack has been modified in the GPT-5.5 release window, especially around artifact/document/spreadsheet tooling and Python startup hooks. They do **not** by themselves prove that every observed change first appeared exactly on GPT-5.5 launch day.

## Most plausible 5.5-era changes visible from the sandbox
1. Heavier artifact-tool initialization at Python startup.
2. New or newly-prioritized artifact-tool aliasing/operation-recording behavior.
3. Additional spreadsheet/runtime warming flags in the Python tool environment.
4. A post-release edit to `sitecustomize.py`, suggesting active iteration on the hook chain after release.

## What is not proven yet
- Exact before-vs-after diff from a pre-2026-04-21 sandbox.
- Whether these changes are universal across all model tiers or only some ChatGPT runtimes.
- Whether the Apr 28 `sitecustomize.py` edit improved anything or added more overhead.
