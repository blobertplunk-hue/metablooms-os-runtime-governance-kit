# Workflow Regression Checklist v5
# Inherits all v1-v4 checks. Adds v5 (AMEND-0005 through AMEND-0008).

## Inherited from v1
- [ ] Artifact-first claims remain required.
- [ ] SEE via web search remains required for non-expert or current claims.
- [ ] CE packet remains required for each processed artifact.
- [ ] Chunking and stop-after-receipt remain required.
- [ ] Every new output artifact is listed in the manifest and receipt.
- [ ] Every amendment has an observation trigger and evidence binding.
- [ ] The amendment is reversible or supersedable.
- [ ] The next queue state names the active workflow version.

## From v2 (GW1 HTML governance)
- [ ] Stage packet declares target layer, allowed mutations, forbidden mutations, and protected contracts.
- [ ] HTML/runtime changes preserve validated answer truth after validation.
- [ ] Native controls used when sufficient; ARIA/custom widgets have explicit justification.
- [ ] Generation/runtime failures have visible DOM error states.
- [ ] No inert window.X observer/wrapper accepted without proven definition/boot assignment.
- [ ] Choice selection states reset both selected and deselected controls.
- [ ] HTML outputs undergo conformance validation or record an evidence-backed waiver.

## From v3 (governance taxonomy)
- [ ] Each stage receipt declares artifact_type and job_type.
- [ ] Each stage receipt lists selected governance categories.
- [ ] Each stage receipt lists intentionally not selected categories when relevant.
- [ ] A gate is not applied merely because it exists; relevance must be justified.
- [ ] Runtime HTML stages distinguish accessibility, telemetry, runtime, education, and kernel gates.

## From v4 (Nomotic governance)
- [ ] Stage receipts include role attributes and context attributes.
- [ ] Gate selection remains scoped; no universal runtime governance unless required.
- [ ] Runtime patches include PDP/PEP boundary evidence.
- [ ] Policy decisions are logged with policy id, input, tier, decision, and fallback.
- [ ] Block/degrade outcomes have accessible visible DOM status path.
- [ ] Structural receipt binding includes workflow version, artifact SHA, selected policies, and output hashes.
- [ ] Deferred cryptographic signing is not falsely claimed as implemented.

## v5 — Mid-Chunk Interrupt + Autonomous Sidecars + Memory Bridge + Runtime Pulse

- [ ] IC conditions (IC-1 through IC-6) evaluated after each artifact within a chunk.
- [ ] If any IC condition fired: INTRA_CHUNK_INTERRUPT_RECEIPT written before continuing.
- [ ] W0-W1 executed on interrupt; W2-W3 executed if classification is defect or gap.
- [ ] Chunk did NOT continue past an unresolved defect/gap interrupt.
- [ ] If same failure class occurred 2+ times: autonomous sidecar generated.
- [ ] Sidecar written to /mnt/data/workflow_sidecars/ with index and SHA for every file.
- [ ] If sidecar blocked: SIDECAR_BLOCKED_RECEIPT written instead.
- [ ] CLAUDE_MEMORY_SYNC_v1.json written at end of session before export.
- [ ] Memory sync contains: current_stage, baseline_sha, active_amendments, open_ic_triggers, session_note.
- [ ] Runtime pulse log (RUNTIME_PULSE_LOG_v1.jsonl) has pre and post entries for each artifact.
- [ ] No artifact was processed while RP-PRE-4 (open IC trigger from prior artifact) was unresolved.
- [ ] T1 pulse failures resulted in block (not warn) before artifact processing began.
