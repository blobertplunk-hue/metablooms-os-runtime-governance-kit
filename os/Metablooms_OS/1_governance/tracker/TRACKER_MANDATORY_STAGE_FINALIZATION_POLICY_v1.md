# TRACKER Mandatory Stage Finalization Policy v1

Status: active after FL17-MERGE-3.

This policy repairs the FL17 regression where the tracker finalization hook existed but was not enforced for post-FL8 stages.

## Mandatory rule
Every bounded governed MetaBlooms stage must complete in this order:

1. Write stage validation report.
2. Write final receipt.
3. Write final handoff.
4. Run `TRACKER_STAGE_FINALIZATION_HOOK_v1.py`.
5. Validate that `runtime/state/TRACKER_STATE_v1.json` binds the current stage, receipt, handoff, preview, and evidence.
6. Render the compact tracker first in the final response.

## Stale state failure
A tracker state is stale if its `current_stage`, `evidence`, or `history` do not bind to the latest completed stage receipt and handoff. Stale tracker state blocks promotion/export and requires repair before continuation.

## Governance layering
Always-on MetaBlooms governance is mandatory baseline. Cartridge governance is additive and never replaces baseline governance.

## Layout rule
The inline tracker must use the compact mobile-safe stacked format beginning with `TRACKER ▸`. Box drawing, right-border pipe-table layouts, and fake determinate progress are forbidden.
