# MetaBlooms External Review Matrix v1

Created UTC: `20260501T040110Z`

Scale: 0=absent, 1=critical gap, 2=partial descriptive support, 3=developing executable support, 4=strong executable support, 5=proven/replayable best-in-class support.

| Expert lens | Score | Priority | Current OS evidence | Gap | Governed cartridge |
|---|---:|---|---|---|---|
| Evals | 2.5 | P1 | Existing eval folders and behavior receipts exist, but current cartridge quality is uneven and there is no universal minimum viable eval loop, trace review protocol, or validator-alignment suite. | Missing cross-cartridge examples, trace-review rubrics, regression cases, validator meta-evals, and improvement metrics. | `EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE` |
| State/checkpointing | 3.0 | P2 | OS has receipts, handoffs, pointers, and authority files; boot executor passes with accepted git_dir_missing warning. | No single durable checkpoint object with thread/resume semantics, state diff, rollback pointer, and human approval interrupt model. | `STATE_CHECKPOINT_RESUME_AND_INTERRUPT_CARTRIDGE` |
| Agent harness | 2.5 | P1 | Stage boundaries and routers exist; archive method router and tool reliability policy are now present. | No canonical stage graph runtime, no multi-agent/worktree isolation, no branch-per-stage diff model, and no formal agent handoff protocol. | `AGENT_HARNESS_STAGE_GRAPH_AND_WORKTREE_CARTRIDGE` |
| Software quality | 3.0 | P2 | Boot/export validation, checksum sidecars, and fail-closed receipts are strong; 7zz independent archive validator is integrated. | Critical path is still fragmented across prompts and scripts; too many governance artifacts are not proven executable gates. | `SOFTWARE_QUALITY_CRITICAL_PATH_CLI_AND_TEST_CARTRIDGE` |
| Security | 2.5 | P1 | There are sandbox/router policies and forbidden-method artifacts; fail-closed posture exists. | No complete artifact threat model, malicious receipt detector, prompt-injection sanitizer, authority poisoning test, or least-privilege tool policy coverage matrix. | `SECURITY_ARTIFACT_THREAT_MODEL_AND_INJECTION_CARTRIDGE` |
| Observability | 2.5 | P1 | Receipts and handoffs create audit data; method reliability observations are beginning to persist. | No unified trace/span schema, searchable execution timeline, failure clustering, or cross-stage causal graph. | `OBSERVABILITY_TRACE_SPAN_LEDGER_CARTRIDGE` |
| Education validity | 2.5 | P1 | The OS repeatedly targets TEKS/STAAR artifacts and includes instructional constraints in prior workflows. | No universal education-validity rubric, student-facing usability eval, misconception-evidence loop, or learning-gain proxy cartridge across generated materials. | `EDUCATION_VALIDITY_LEARNING_EFFICACY_CARTRIDGE` |
| UX/product simplicity | 1.5 | P0 | Power-user workflow is possible, but normal operation still depends on long prompt incantations and dense terminology. | No minimal operator surface such as mb boot/run/verify/export/replay, no one-screen critical path, and no plain-English state dashboard. | `UX_OPERATOR_SURFACE_AND_CRITICAL_PATH_SIMPLIFICATION_CARTRIDGE` |
| Artifact portability | 4.0 | P3 | Strongest current lens: complete export exists with SHA sidecar, 7zz router, 2590 entries, and independent archive testing. | Needs automatic fresh-download/fresh-extract/fresh-boot replay proof for every promoted export, plus stale-authority quarantine and sidecar binding enforcement. | `ARTIFACT_PORTABILITY_REPLAY_PROOF_CARTRIDGE` |

## Created cartridge specs

- `EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_SPEC_v1.json`
- `STATE_CHECKPOINT_RESUME_AND_INTERRUPT_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/STATE_CHECKPOINT_RESUME_AND_INTERRUPT_CARTRIDGE_SPEC_v1.json`
- `AGENT_HARNESS_STAGE_GRAPH_AND_WORKTREE_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/AGENT_HARNESS_STAGE_GRAPH_AND_WORKTREE_CARTRIDGE_SPEC_v1.json`
- `SOFTWARE_QUALITY_CRITICAL_PATH_CLI_AND_TEST_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/SOFTWARE_QUALITY_CRITICAL_PATH_CLI_AND_TEST_CARTRIDGE_SPEC_v1.json`
- `SECURITY_ARTIFACT_THREAT_MODEL_AND_INJECTION_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/SECURITY_ARTIFACT_THREAT_MODEL_AND_INJECTION_CARTRIDGE_SPEC_v1.json`
- `OBSERVABILITY_TRACE_SPAN_LEDGER_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/OBSERVABILITY_TRACE_SPAN_LEDGER_CARTRIDGE_SPEC_v1.json`
- `EDUCATION_VALIDITY_LEARNING_EFFICACY_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/EDUCATION_VALIDITY_LEARNING_EFFICACY_CARTRIDGE_SPEC_v1.json`
- `UX_OPERATOR_SURFACE_AND_CRITICAL_PATH_SIMPLIFICATION_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/UX_OPERATOR_SURFACE_AND_CRITICAL_PATH_SIMPLIFICATION_CARTRIDGE_SPEC_v1.json`
- `ARTIFACT_PORTABILITY_REPLAY_PROOF_CARTRIDGE` → `0_kernel/cartridges/external_review_lenses/ARTIFACT_PORTABILITY_REPLAY_PROOF_CARTRIDGE_SPEC_v1.json`
