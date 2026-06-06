# TRACKER_STATE_UPDATE_PROTOCOL_v1

## Purpose
Bind every governed stage completion to a deterministic inline tracker state update.

## Rule
After a bounded stage writes its receipt and handoff, the tracker state MUST be updated before the next governed action is claimed.

## Required update order
1. Load `runtime/state/TRACKER_STATE_v1.json`.
2. Verify the stage receipt exists and hash it.
3. Verify the stage handoff exists and hash it.
4. Append receipt/handoff evidence items to tracker state.
5. Append a history entry for the completed stage.
6. Set the new `current_stage`, `status`, `stage_index`, `progress_label`, `now`, `next_allowed_action`, and `stop_rule`.
7. Render the tracker with `TRACKER_RENDERER_v1.py`.
8. Validate the rendered tracker starts with the project-tracker marker before any governed response body.

## Fail-closed conditions
- Missing prior state.
- Missing or unreadable receipt.
- Missing or unreadable handoff.
- Handoff does not authorize the requested next stage.
- Receipt or handoff evidence is omitted from tracker state.
- Rendered tracker does not start with `╭─ PROJECT TRACKER`.
- Determinate progress is claimed without a known stage denominator.

## Scope boundary
This protocol wires state/handoff binding only. It does not implement smoke-test or export packaging.
