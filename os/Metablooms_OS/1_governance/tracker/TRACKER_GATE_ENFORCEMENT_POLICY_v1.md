# TRACKER_GATE_ENFORCEMENT_POLICY_v1

The inline project tracker is a governed response gate, not decorative output.

## Enforcement order
1. Load `/mnt/data/Metablooms_OS/runtime/state/TRACKER_STATE_v1.json`.
2. Validate state shape and evidence requirements.
3. Render the tracker as the first visible block of the response.
4. Confirm the requested stage is the latest handoff-authorized bounded stage.
5. Run one bounded stage only.
6. Write receipt, handoff, validation report, manifest, and bundle.
7. Update tracker state only within the authorized stage scope.
8. Stop before the next stage.

## Accessibility / status principle
The tracker must include explicit text labels for status, progress, blockers, next action, and stop rule. It must not rely on color alone or hidden UI state.

## Fail-closed rule
If state is missing, malformed, not renderable, or unsupported by evidence for DONE/BLOCKED claims, block governed action and report the blocker.
