# FL16 / FL17 Semantic Authority Policy v1

Created: 20260430T015900Z
Stage: FL17-MERGE-4_SEMANTIC_RECONCILIATION

## Rule

Export/package PASS is not promotion PASS.

FL17's export metadata may be treated as evidence that an archive was packaged and provenance-bound. It must not be treated as evidence that FL16 passed promotion. FL16 remains `BLOCKED_NOT_PROMOTED` until a later explicit promotion stage writes a passed receipt and handoff.

## Mandatory interpretation

- FL16 receipt status: `blocked_before_promotion`
- FL16 receipt verdict: `BLOCKED_NOT_PROMOTED`
- FL16 promotion decision: `NOT_PROMOTED`
- FL17 export manifest verdict: `PASS`
- FL17 contains through: `FAILURE-LEARNING-16_VALIDATE_AND_PROMOTE_FL15_FULL_EXPORT_WITH_PYTHON_S`

## Prohibited inference

Do not treat `contains_through_stage` or export manifest `PASS` as proof that every contained stage passed promotion gates.

## Required future gate

Before any baseline promotion, the next stage must verify: candidate export integrity, active pointer target, tracker lifecycle freshness, receipt/handoff status, and explicit promotion authority.
