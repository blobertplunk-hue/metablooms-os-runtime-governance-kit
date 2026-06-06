# STAAR ENGINE SOP — GENERALIZED
## Research-Governed Workflow for Building Any TEKS Engine
**Version:** v34  
**Scope:** General method only. TEKS-specific content must come from TEKS-specific artifacts. Subset-specific requirements for single-file HTML runtimes, adaptive multi-family engines, export packaging, and repair workflows may extend this SOP in appendices, but may not weaken its core gates.

---

## 1. PURPOSE

This SOP governs **how** to build, patch, validate, and harden a STAAR-aligned TEKS engine for any target TEKS.

It does **not** hardcode TEKS-specific:
- family registries
- misconceptions
- validators
- response modes
- visual subsystems
- released-item inventories
- challenge gates
- format stamps
- distractor patterns

Those must come from TEKS-specific source packets and contract bundles.

This SOP distinguishes between:
- shipping artifacts and support artifacts
- structural correctness and style/tightness heuristics
- released-template fidelity and generic TEKS-topic alignment

An engine that is merely runnable or merely TEKS-aligned does not satisfy this SOP unless it also meets the relevant fidelity, export-truth, and artifact-verification gates defined below.

---

## 2. SOURCE HIERARCHY

Resolve conflicts in this order:

1. Released STAAR source materials
2. TEKS-specific source packet
3. TEKS-specific contract bundle
4. TEKS-specific SOP
5. General STAAR engine SOP
6. Current runtime HTML
7. Prior receipts, audits, and reports

Earlier sources override later sources.

When released items are a primary source, implementation must be driven by a **released-template mapping artifact** that converts source items into runtime families, renderer obligations, reasoning modes, and distractor archetypes before coding begins.

---

## 3. UNIVERSAL INVARIANTS

These apply to every TEKS engine.

### 3.1 Validate Before Render
No item may render until it passes structural validation, family validation, and answer-key coherence checks.

### 3.2 Post-Render Coverage Truth
Coverage is committed only after successful render of a valid item.

### 3.3 No Dead Families
Any family present in the registry must have a reachable, working generator path.

### 3.4 No Silent Fallback Collapse
A generator/router may not silently collapse the engine into one always-valid family when other required families fail.

### 3.4A Fail-Closed After Eligible Family Exhaustion
In adaptive multi-family engines, fail-closed behavior must trigger only after all currently eligible families in the active routing cycle have failed generation or validation. A single blocked family may not monopolize routing into premature halt.

### 3.5 Single Runtime Truth
Challenge, mastery, coverage, diagnostics, and gating must derive from one canonical runtime state model.

### 3.6 Family Fidelity Over “Close Enough”
If the contract requires a family, subsystem, validator path, or response mode, a similar substitute does not count.

### 3.6A Reasoning-Mode Fidelity
If a released item family is comparative, inferential, descriptive, or estimation-based, the runtime family must preserve that reasoning mode. A direct-read substitute does not count as fidelity.

### 3.7 Teacher Diagnostics Required
Each engine must surface enough teacher/debug telemetry to detect:
- dead families
- rendered-vs-selected drift
- fallback reasons
- validation failures
- misconception concentrations
- challenge/mastery gate state

### 3.7A Runtime Observability Minimum
Where applicable, teacher/debug telemetry must expose generator fallback reasons, chooser reasons, recent validation failures, family counts, and challenge/mastery gate state.

### 3.8 Smallest Valid Change
When patching, preserve stable architecture and apply the smallest bounded fix that restores correctness.

### 3.9 Artifact Truth Over Claimed Repair
A repair, export, or completion claim is not valid until it is verified against the exact exported artifact on disk. Conversation-level intent or intermediate tool output does not count as proof of change.

---

## 4. REQUIRED BUILD ARTIFACTS

For each TEKS engine, the workflow must produce or maintain:

- released-item source packet
- released-template mapping artifact when released items are a primary source
- TEKS-specific contract bundle
- TEKS-specific SOP
- engine HTML or locked shipping artifact
- validation packet
- coverage audit
- stage receipts
- continuity/handoff notes
- export receipt for any downloadable shipping artifact

If one of these is missing, mark it explicitly as missing or blocked.

Any receipt that cites a source artifact must verify that the cited source exists at finalization time. When feasible, receipts should record source and output hashes.

---

## 5. REQUIRED WORKFLOW

### Stage 0 — Target Lock
Record:
- grade
- subject
- TEKS code
- engine scope
- authoritative source set
- shipping artifact type
- support artifact types
- deployment target
- success criterion for the shipping artifact

Support artifacts do not satisfy engine delivery unless they are explicitly locked as the shipping artifact.

### Stage 1 — Research and Artifact Discovery
Locate and read:
- released STAAR items
- TEKS-specific source packets
- TEKS-specific contract bundles
- TEKS-specific SOPs
- current engine runtime
- prior audits and receipts

If released items are used, identify:
- dominant released item archetypes
- recurring stimulus templates
- reasoning modes
- named distractor trap classes
- interaction-mode obligations where evidenced

### Stage 2 — Contract Lock
Extract and lock:
- family registry
- item types
- visual subsystems
- validator obligations
- scaffold obligations
- challenge/mastery obligations
- format stamps
- excluded/deferred families
- released-template map
- reasoning modes per family
- distractor archetypes / trap classes
- shipping artifact lock
- stimulus renderer contract where recurring visuals exist
- interaction fidelity obligations where released modes require them

No coding starts before contract lock, released-template mapping, and shipping-artifact lock are complete.

### Stage 3 — Pre-Code Compliance Table
For every family:
- contract family id
- runtime family id
- exact match / mismatch
- contract item type
- runtime item type
- contract visual subsystem
- runtime subsystem
- contract validator requirement
- runtime validator path
- surfaced in runtime? yes/no
- fix required
- released template mapped? yes/no
- reasoning mode match? yes/no
- distractor trap classes defined? yes/no
- stimulus renderer contract present? yes/no
- shipping artifact target preserved? yes/no
- exemplar/template parity required? yes/no
- exemplar/template parity status

Any unresolved row blocks implementation for that family.

If the build claims exemplar-shell or template transplant, unresolved parity rows for required inherited shell subsystems also block implementation.

### Stage 4 — Bounded Implementation
Patch one bounded subsystem at a time.

Recommended order:
1. validator contract
2. post-render coverage truth
3. deterministic generator contract
3A. seed-bank vs validator compatibility
3B. family-safe fallback contract
4. chooser / anti-starvation logic
4A. visible-type monotony guard when applicable
5. challenge/mastery truth
6. released-format fidelity upgrades
6A. released-template parity upgrades
6B. interaction-fidelity preservation where required
7. teacher diagnostics
8. maintainability hardening

### Stage 5 — Immediate Validation
After each bounded patch:
- syntax check
- validator check
- targeted subsystem check
- regression check
- readback verification against the exact output artifact
- receipt write

For single-file or browser-based HTML engines, immediate validation must also include:
- script parse/syntax pass
- initial render smoke test
- DOM reference integrity check when runtime selectors or overlays are modified

For repair stages, validation must confirm:
- the old buggy token/pattern is absent where applicable
- the intended new token/pattern is present where applicable
- the intended target function or gate was actually modified in the exported artifact

Broken or validation-failed outputs are provisional only and may not be promoted as current best or used as the next-stage base.

### Stage 6 — Continuity
Write:
- what changed
- what passed
- what remains
- exact next stage

Stage completion also requires artifact presence verification. Any artifact named in a receipt, report, or handoff must exist at the declared path before the stage is marked complete.

If multiple artifacts exist for one TEKS, continuity must distinguish:
- current best engine
- latest slice set
- SOP/contract only
- missing/no accessible engine

---

## 6. RECURSIVE RESEARCH LOOP (MANDATORY)

Research is not one pass. It is recursive.

### 6.1 Trigger Conditions
Run recursive research when any of the following are true:
- source coverage is incomplete
- a family is weak, missing, or shallow
- a subsystem is only “close enough”
- the runtime repeats, starves, or deadlocks
- the validator is too weak
- mastery logic drifts from coverage truth
- released-item fidelity is uncertain
- a patch plan depends on current prompting/agent/workflow guidance
- released-template mapping is incomplete
- exemplar/template parity is uncertain
- exported artifact truth is uncertain
- a valid seed fails its runtime validator
- student-visible monotony persists despite internal family diversity

### 6.2 Recursive Loop
For the active problem, repeat this loop:

1. **Question** — state the exact unresolved problem.
2. **Search** — search authoritative external sources first; prefer official sources; then use high-quality secondary sources only if needed.
3. **Extract** — pull only the load-bearing claims relevant to the problem.
4. **SEE pass** — validated claims, conflicts/limits, confidence, and what is source-backed vs local-runtime-only.
5. **CE pass** — mechanism, implications, design rule, implementation consequence.
6. **Gap test** — compare findings against the current SOP, contract, and runtime.
7. **Improve** — update the plan, validator, contract, runtime, or SOP.
8. **Re-evaluate** — ask whether the new evidence or new patch materially improves correctness, fidelity, or debuggability.
9. **Repeat** — continue until one of the stop conditions is met.

### 6.3 Stop Conditions
Recursive research stops only when:
- no new authoritative source changes the current design rule, and
- no newly found evidence produces a meaningful implementation improvement, and
- the remaining uncertainty is local-runtime-specific rather than externally researchable

If improvement is still possible, research is not complete.

### 6.4 Required Output of Research
Each recursive research pass must produce:
- research question
- sources searched
- validated claims
- rejected/qualified claims
- resulting design rules
- exact runtime/SOP updates caused by the pass
- released-template map updates when applicable
- exact fidelity gaps by family / renderer / reasoning mode
- export-truth or lineage-truth updates when applicable

---

## 7. GENERALIZED PROMPTING / AGENT WORKFLOW RULES

When an LLM is building or patching an engine, the prompt/governance must require:
- clear success criteria
- explicit staged workflow
- exact output requirements
- eval/validation expectations
- no hidden substitutions
- no completion claims without evidence
- reusable prompt versioning when applicable
- iterative improvement based on eval results

For complex tasks, prompt chains/workflow stages are preferred over one giant undifferentiated instruction block.

Prompt/governance for engine-building stages must require the model to distinguish:
- shipping artifact vs support artifacts
- current best vs provisional outputs
- structural validators vs style/tightness heuristics
- released-template fidelity vs generic TEKS coverage

---

## 8. ARCHITECTURE STANDARD FOR SINGLE-FILE HTML ENGINES

Recommended module order inside one file:
1. Family registry
2. Contracts / schemas
3. Store / state
4. Coverage engine
5. Generator registry
6. Validator
7. Render engine
8. Controller / submit logic
9. Persistence
10. Diagnostics / invariants

Do not let the file degrade into an uncontrolled switch pile with scattered hidden state.

Dynamic interactive controls in shipped runtime code must use DOM-safe creation and binding methods or an equivalently safe mechanism. Fragile inline-handler string interpolation is forbidden.

Touch-safe alternate inputs may supplement required released interaction modes, but may not replace them unless the contract explicitly permits substitution and preserves the same scoring semantics.

---

## 9. REQUIRED VALIDATION DOMAINS

Every engine must validate at least these domains:

### 9.1 Structural
- item shape
- required fields
- response mode
- choice count
- answer count
- shipping artifact is real runtime content, not scaffold/stub/placeholder
- source/output artifact identity is internally consistent where receipt claims lineage

### 9.2 Family-Specific
- family-specific constraints
- family-specific answer-key coherence
- family-specific visual / prompt consistency
- released reasoning-mode match where applicable
- released trap-class presence where evidenced
- seed-bank compatibility with runtime validator where applicable

### 9.3 Runtime
- no dead families
- rendered-vs-selected truth
- no silent fallback collapse
- fail-closed only after eligible family exhaustion where applicable
- no early visible monotony
- student-visible monotony audit where applicable
- challenge/mastery truth
- runtime observability minimums where adaptive generation exists

### 9.4 Fidelity
- released-family identity
- released interaction mode
- released directionality
- released reasoning-mode fidelity
- released distractor trap classes where evidenced
- released stimulus-template fidelity where recurring visuals exist
- exemplar/template parity where exemplar-shell or template transplant is claimed

### 9.5 Export Truth
- exact shipped artifact reopened from disk
- exported/downloadable copy verified where requested
- receipt fields sufficient to verify source/output truth
- no false completion claims based on intermediate artifacts

---

## 10. FAILURE CLASSES TO CHECK EVERY TIME

At minimum, audit for:
- validator too weak
- family exists in code but is not reachable
- family reachable but not surfaced
- family surfaced but mislabeled to the student
- generator null fragility
- silent fallback masking
- challenge truth drift
- score-vs-mastery drift
- selected-vs-rendered drift
- visual subsystem substitution
- repeated visible type despite family diversity
- missing released interaction fidelity
- wrong shipping artifact locked or evaluated
- placeholder or scaffold export
- source-lineage false or missing
- patch not landed in exported artifact
- runtime not executable
- released-template map missing or incomplete
- reasoning-mode mismatch
- released trap absent or shallow
- stimulus renderer contract missing or invalid
- seed-bank vs validator incompatibility
- premature halt before eligible family exhaustion
- valid family blocked by style/tightness heuristic
- exemplar/template parity false claim
- bundle completeness misrepresented
- current-best promotion without required validation

Any newly discovered failure class must be written back into governance artifacts, not left only in chat.

---

## 11. EXPORT / HANDOFF RULE

A handoff is incomplete unless it includes:
- current best engine artifact or explicitly classified alternative status
- current governing SOP
- current TEKS-specific SOP
- current contract bundle
- latest validation/report/receipt set
- explicit next stage

No export is complete until:
- the exact shipped artifact has been reopened from disk
- the shipped artifact is verified as real runtime content, not scaffold or placeholder
- if a downloadable copy is requested, the final downloadable copy exists at the declared path
- the receipt records at minimum source path, final path, existence status, and final size in bytes
- any cited source artifact in the receipt has been existence-checked at finalization time

Bundle manifests must classify each TEKS entry as one of:
- current best engine
- latest slice set
- SOP/contract only
- missing/no accessible engine

---

## 12. FINAL RULE

The general SOP governs the method.
The TEKS-specific artifacts govern the content.
Research continues recursively until further authoritative search no longer produces meaningful improvement.
No engine is complete merely because it runs.
It is complete only when it is:
- source-backed
- contract-exact
- validated
- artifact-audited
- exported truth-verified
- faithful to the required released-template / exemplar obligations for its build class

---

## APPENDIX A — MINIMUM RESEARCH CHECKLIST

Before calling research complete, confirm:
- released items reviewed
- TEKS-specific packet reviewed
- contract locked
- official current prompting/agent workflow guidance checked when relevant
- validation/eval implications extracted
- research loop ended because of stop conditions, not impatience
- released-template map created when released items are primary
- dominant reasoning modes identified
- recurring stimulus templates identified where applicable
- named distractor trap classes extracted where evidenced
- shipping artifact locked before implementation
- fidelity gaps distinguished from generic TEKS coverage gaps

---

## APPENDIX B — SINGLE-FILE HTML / BROWSER RUNTIME ADDENDUM

Apply this appendix when the shipping artifact is a single-file HTML or browser-based runtime.

Required gates:
- Executable Runtime Gate for HTML Engines
- DOM Reference Integrity Validator
- DOM-Safe Dynamic Interaction Rule
- Touch-safe alternate input preservation rule

### B.1 Executable Runtime Gate for HTML Engines
Stage completion requires:
- JavaScript syntax/parse pass
- initial render smoke test
- required runtime regions populate without immediate runtime failure

### B.2 DOM Reference Integrity Validator
Any DOM node, overlay, button, selector, or event target referenced by runtime logic must exist in the exported document or be guarded by null-safe logic.

### B.3 DOM-Safe Dynamic Interaction Rule
Dynamic interactive controls must be created with DOM-safe node creation and explicit event binding, or an equivalently safe mechanism.

### B.4 Touch-Safe Alternate Input Preservation
If a released interaction mode is required, the engine must preserve that mode. A touch-safe alternate path may supplement it only if it preserves the same scoring semantics.

---

## APPENDIX C — ADAPTIVE MULTI-FAMILY ENGINE ADDENDUM

Apply this appendix when the engine contains multiple families, adaptive routing, dynamic generation, or rescue/coverage scheduling.

Required gates:
- Seed-Bank vs Validator Compatibility Gate
- Fail-Closed After Eligible Family Exhaustion
- Deterministic Family-Safe Fallback Contract
- Minimum Runtime Diagnostics and Observability Rule
- Student-Visible Repetition Audit

### C.1 Seed-Bank vs Validator Compatibility Gate
Before export, every canonical and released-style seed must pass the same family validator used at runtime.

### C.2 Fail-Closed After Eligible Family Exhaustion
No single blocked family may halt the engine unless all currently eligible families in that cycle have failed generation/validation.

### C.3 Deterministic Family-Safe Fallback Contract
Fallbacks must preserve family or format intent whenever possible. Generic collapse into one always-valid family is forbidden unless no family-safe fallback exists and the reason is logged.

### C.4 Minimum Runtime Diagnostics and Observability Rule
Teacher/debug diagnostics must expose, at minimum where applicable:
- selected family counts
- rendered family counts
- chooser reasons
- generator/fallback reasons
- recent validation failures
- challenge/mastery gate state
- recent rerolls
- blocked-family counts

### C.5 Student-Visible Repetition Audit
Coverage must be audited at both internal family level and student-visible type level. The engine must guard against visible monotony even when internal diversity appears high.

---

## APPENDIX D — EXPORT / PACKAGING / PROMOTION ADDENDUM

Apply this appendix when packaging bundles, downloadable artifacts, or multi-artifact handoffs.

Required rules:
- Downloadable Export Verification and Receipt Minimums
- Bundle Completeness Classification Rule
- Current-Best Promotion Rule
- Provisional Failure and Non-Promotion Rule

### D.1 Downloadable Export Verification and Receipt Minimums
If a downloadable is requested, produce a final downloadable copy in `/mnt/data`, verify existence, record final size in bytes, and write a receipt containing:
- source path
- final downloadable path
- source existence status
- downloadable existence status
- final size in bytes

### D.2 Bundle Completeness Classification Rule
Any bundle or export manifest must classify each TEKS entry as:
- current best engine
- latest slice set
- SOP/contract only
- missing/no accessible engine

### D.3 Current-Best Promotion Rule
An artifact may be labeled current best only if it:
- passes required validation
- is named in a receipt
- clearly supersedes prior lineage

Slice sets may not be promoted as unified current-best engines unless a unified artifact exists.

### D.4 Provisional Failure and Non-Promotion Rule
Any syntax-failed, validation-failed, or runtime-broken artifact is provisional only and may not be promoted as current best, bundled as final, or used as next-stage source.

---

## APPENDIX E — REPAIR / PATCH VERIFICATION ADDENDUM

Apply this appendix when patching existing runtimes or executing bounded repair stages.

Required rules:
- Patch Readback Parity Gate
- Property-Schema Consistency Validator
- Machine-Readable Repair Receipt and Patch Manifest

### E.1 Patch Readback Parity Gate
Every claimed fix must be verified against the exported artifact itself. Confirm:
- old buggy token/pattern absent where applicable
- intended new token/pattern present where applicable
- intended target function or gate actually modified

### E.2 Property-Schema Consistency Validator
Shared helper-object outputs and property schemas must be asserted and cross-checked. References to undeclared aliases or incompatible schema keys block export.

### E.3 Machine-Readable Repair Receipt and Patch Manifest
Every repair pass must write a structured companion artifact containing:
- source artifact path
- output artifact path
- changed functions
- removed bug signatures
- added fix signatures
- validation checks run
- pass/fail result
- output hash
