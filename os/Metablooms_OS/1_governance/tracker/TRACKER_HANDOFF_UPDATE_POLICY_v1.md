# TRACKER_HANDOFF_UPDATE_POLICY_v1

Every governed MetaBlooms stage must leave the inline project tracker in a post-stage state before the response claims completion.

## Mandatory sequence
- Receipt and handoff are written.
- Tracker state is updated from those files.
- Tracker render preview is generated after the update.
- Handoff-update validator confirms receipt/handoff evidence binding and render-first marker.
- The response begins with the rendered tracker.

## Rejection rules
Reject a governed response if it claims DONE or BLOCKED without matching receipt/handoff evidence in `runtime/state/TRACKER_STATE_v1.json`, or if the first visible response block is not the tracker.
