---
status: accepted
category: governance
created_utc: 2026-04-28T00:00:00Z
refactor_stage: R2_ADR_EXTRACTION_AND_ARCHIVAL_CONVERSION
supersedes:
  - 1_governance/workflow_v6/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json
---
# Split rationale from runtime contracts

## Context and Problem Statement

MetaBlooms inherited `CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json` as a mixed-purpose artifact. It contains historically useful context, role handoff notes, track summaries, and SHA anchors, but it also reads like live runtime authority. That creates a governance hazard because historical narrative can be mistaken for executable contract truth.

## Decision Drivers

* Artifact-first runtime authority must be machine-verifiable.
* Historical rationale must remain readable and reviewable.
* Live contracts must be lean, current, and validator-friendly.
* Stale deployment instructions must not masquerade as active runtime control.

## Considered Options

* Keep the cross-link document as a live runtime JSON.
* Delete the cross-link document after extracting successor logic.
* Preserve the document as legacy archive material and move active rules into explicit contracts.

## Decision Outcome

Chosen option: **Preserve the document as legacy archive material and move active rules into explicit contracts**, because this keeps the historical record while preventing narrative handoff content from being treated as runtime authority.

### Consequences

* Good, because rationale and lineage remain inspectable in a stable archival artifact.
* Good, because successor compatibility rules can be validated independently.
* Good, because operator instructions and historical track notes stop polluting live contract scope.
* Bad, because migration requires a redirect layer and successor contracts.
* Bad, because some previously co-located information is now split across archive and contract artifacts.

### Confirmation

* `legacy_artifact_redirects_v1.json` points the cross-link source artifact to its archive and successor targets.
* `unified_runtime_compatibility_contract_v1.json` is created and validated in R3.
* The legacy cross-link file is treated as archival context rather than active runtime authority.

## Pros and Cons of the Options

### Keep the cross-link document as a live runtime JSON

* Good, because no migration work is required.
* Bad, because historical instructions and track notes remain mixed with active governance data.
* Bad, because the file is stale-prone and difficult to validate as policy.

### Delete the cross-link document after extracting successor logic

* Good, because only live artifacts remain.
* Bad, because the historical explanation of why the split happened would be lost.
* Bad, because audit trails become weaker.

### Preserve the document as legacy archive material and move active rules into explicit contracts

* Good, because it separates historical rationale from machine-enforced policy.
* Good, because successor contracts can be schema-checked and regression-tested.
* Neutral, because a redirect layer is required to preserve discoverability.

## More Information

The archived source for this decision is retained at `runtime/governance/legacy_archives/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json`.
