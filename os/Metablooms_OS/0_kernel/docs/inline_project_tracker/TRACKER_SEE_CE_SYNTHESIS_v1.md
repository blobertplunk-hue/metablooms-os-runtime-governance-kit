# TRACKER_SEE_CE_SYNTHESIS_v1

## SEE findings

### Validated claims

1. ChatGPT currently supports richer visual/interactive response surfaces such as visual responses and interactive code blocks, but these are not equivalent to an always-on custom project tracker injected into every future response.
2. Canvas is useful for writing/coding projects, but current official guidance does not make it a reliable Android/mobile enforcement surface.
3. UX guidance supports persistent, timely status feedback for long-running tasks.
4. Accessibility guidance supports explicit status text and prohibits using numeric progress when progress is unknown.
5. Project-status reporting guidance supports compact fields: progress, health/status, blockers, risks, next steps, and evidence/action items.

### Inferences

1. The safest immediate tracker is an inline Markdown/plain-text block rendered at the top of every governed response.
2. A richer HTML/canvas tracker should be generated later as a secondary artifact, not as the enforcement layer.
3. The tracker must be artifact-backed because ChatGPT UI state and chat memory cannot be treated as deterministic runtime state.

## CE synthesis

### Design constraints converted to architecture

- UX principle: visibility of status → `TRACKER_RENDER_GATE`.
- Accessibility principle: status text and determinate/indeterminate distinction → `TRACKER_PROGRESS_GATE`.
- Project-management principle: concise progress/risk/next-step reporting → minimum tracker fields.
- MetaBlooms principle: artifacts over memory → `TRACKER_BOOT_GATE` and `TRACKER_EVIDENCE_GATE`.

### Minimum viable tracker architecture

1. `TRACKER_STATE_v1` stores project/stage/status/evidence fields.
2. `TRACKER_RENDERER_v1` turns state into the compact chat header.
3. `TRACKER_BOOT_GATE_v1` blocks governed execution if state cannot be loaded or initialized.
4. `TRACKER_EVIDENCE_BINDING_v1` binds visible claims to receipt/handoff/hash paths.
5. `TRACKER_PROGRESS_GATE_v1` rejects fake percentages.
6. `TRACKER_HANDOFF_UPDATE_v1` updates state after each bounded stage.

### Implementation sequence recommended

1. Implement schema and example state.
2. Implement renderer spec and static validation.
3. Implement boot/stage gates.
4. Wire into MetaBlooms boot/handoff flow.
5. Run smoke tests.
