# Research Trigger Integration v1

Created: 2026-04-24T00:58:30Z

## Hard invariant

If the user says **research** and has not explicitly requested no web search, the runtime must execute SEE through `web.run` before substantive output. Missing `web.run` is a fail-closed violation.

## Installed artifacts

- `research_trigger_rule_v1.json`
- `interceptor_research_trigger_patch_v1.json`
- `verifier_research_trigger_patch_v1.json`
- `research_trigger_validation_receipt.schema.json`

## Required behavior

1. CE classifies the task as `research_required`.
2. Interceptor schedules `SEE_recursive_v1`.
3. Tool router queues `web.run`.
4. Verifier blocks output if `web.run` evidence/citations are missing.

## Override

Only an explicit user instruction such as “do not browse,” “no web search,” or “do not research” may skip the tool call; that skip requires a warning receipt.
