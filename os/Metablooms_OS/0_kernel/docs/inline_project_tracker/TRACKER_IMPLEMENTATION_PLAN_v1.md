# TRACKER_IMPLEMENTATION_PLAN_v1

Status: plan only; no implementation performed in TRACKER-0.

## Stage TRACKER-1 — Schema and state seed

Create:
- `0_kernel/schemas/TRACKER_STATE_SCHEMA_v1.json`
- `runtime/state/TRACKER_STATE_v1.json`
- `receipts/inline_project_tracker/TRACKER_1_*`

Pass gates:
- JSON schema valid.
- Example state validates.
- Missing denominator produces indeterminate progress.

## Stage TRACKER-2 — Markdown renderer and validator

Create:
- `0_kernel/cartridges/inline_project_tracker/TRACKER_RENDERER_v1.*`
- `0_kernel/cartridges/inline_project_tracker/TRACKER_VALIDATOR_v1.*`

Pass gates:
- Renderer always outputs required fields.
- Renderer starts with `╭─ PROJECT TRACKER`.
- Mobile width check passes.
- Percent rejected without denominator.

## Stage TRACKER-3 — Boot and stage gates

Create:
- `1_governance/tracker/TRACKER_BOOT_GATE_v1.md`
- `1_governance/tracker/TRACKER_STAGE_GATE_v1.md`
- `1_governance/tracker/TRACKER_EVIDENCE_GATE_v1.md`
- `1_governance/tracker/TRACKER_STOP_GATE_v1.md`

Pass gates:
- Missing state produces blocked tracker.
- Existing state loads before governed action.
- Evidence required for DONE/BLOCKED claims.

## Stage TRACKER-4 — Handoff wiring

Create:
- `0_kernel/cartridges/inline_project_tracker/TRACKER_HANDOFF_UPDATE_v1.*`

Pass gates:
- Successful stage updates tracker to next stage.
- Blocked stage records blocker and evidence.
- Done stage records final evidence.

## Stage TRACKER-5 — Smoke audit

Tests:
- boot valid state
- boot missing state
- run stage transition
- blocked transition
- done transition
- stale handoff rejection
- fake percent rejection
- mobile width check

Pass gates:
- All tests produce receipts.
- No implementation claim without artifact evidence.
