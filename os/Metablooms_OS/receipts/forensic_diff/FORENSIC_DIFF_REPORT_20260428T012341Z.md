# Forensic Diff: sandbox changes around GPT-5.5

## Scope
- Compare current live sandbox/runtime fingerprints with prior local sandbox authority artifacts stored in `/mnt/data`.
- Correlate the result with the official GPT-5.5 release window.

## Method
- Live probe of current hook files, env flags, mtimes, and Python startup behavior.
- Inspection of older sandbox docs already present in `/mnt/data/Metablooms_OS/3_data/vault/sandbox`.
- Correlation against the official GPT-5.5 release date: 2026-04-23.

## Confidence limits
- No pre-5.5 full filesystem snapshot of /opt was found in /mnt/data for direct before/after file hashing.
- This packet therefore compares live sandbox state to older sandbox authority artifacts in /mnt/data and to release-window timestamps and official release claims.

## Prior baseline available in /mnt/data
- The older sandbox packet in `/mnt/data/Metablooms_OS/3_data/vault/sandbox` documents resource ceilings and safe operating rules.
- It does **not** document a Python startup hook chain, `.pth` injection path, or `presentation_artifact_tool` import path.
- Therefore, the strongest artifact-backed conclusion is that the old local baseline was focused on watchdog/resource behavior rather than Python boot instrumentation.

## Current live sandbox findings
- `/opt/python-hooks/sitecustomize.py` present; mtime `2026-04-28T01:13:18.563047Z`.
- `/opt/pyvenv/lib/python3.13/site-packages/000_oai_py_sys_path_prepend.pth` present; mtime `2026-04-21T01:48:01Z`.
- `/opt/pyvenv/lib/python3.13/site-packages/oai_py_sys_path_prepend.py` present; mtime `2026-04-21T01:48:01Z`.
- `/opt/pyvenv/lib/python3.13/site-packages/presentation_artifact_tool` present; mtime `2026-04-21T21:29:17Z`.

## Diff assessment
### New or newly salient in the current runtime
- A `.pth` bootstrap path injects OpenAI-specific path rewrites before normal user code runs.
- `sitecustomize.py` is active in the current runtime and eagerly imports artifact/tooling code.
- Environment flags reference artifact-tool initialization and operation recording (`CUA_DD_INIT_ARTIFACT_TOOL_V2`, `...RECORD_OPERATIONS`, spreadsheet runtime warming).

### Not supported as new-from-5.5 with direct proof
- We do **not** have a pre-5.5 `/opt` snapshot in `/mnt/data`, so we cannot prove first appearance on April 23 solely from local artifacts.
- We can only prove that relevant files were modified in the April 21-28, 2026 window and are present now.

## Most defensible conclusion
- The best-supported forensic claim is **not** “GPT-5.5 definitely introduced the hook chain from nothing.”
- The best-supported claim is: **the sandbox/tool-runtime layer was modified in the GPT-5.5 release window, and the current Python regression lives in that shared tool-runtime layer rather than in model weights.**

## Why this matters
- This narrows escalation from a model complaint to a sandbox/runtime regression report.
- It also explains why the issue reproduces under GPT-5.4 after the 5.5-era rollout if both variants share the same sandbox image or hook layer.

## Recommended wording for escalation
> We do not have proof that GPT-5.5 alone introduced the entire chain, but live sandbox forensics show that the Python startup hook/tooling layer was modified in the April 21-28, 2026 window around the GPT-5.5 rollout. The regression is in the shared sandbox runtime: normal `python3` eagerly loads OpenAI-specific `.pth` and `sitecustomize` hooks that import `presentation_artifact_tool`, adding multi-second startup latency and high memory use. `python3 -S` bypasses the problem, which localizes the fault to site initialization rather than Python itself.