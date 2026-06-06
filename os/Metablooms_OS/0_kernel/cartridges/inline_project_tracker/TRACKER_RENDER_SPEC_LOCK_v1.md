# TRACKER_RENDER_SPEC_LOCK_v1

## TRACKER-4R Mobile Reflow Repair

The inline tracker MUST use a compact stacked format. It MUST NOT use box-drawing borders, pipe-table layout, right-side borders, or fixed-width padded cells.

Required default format:

```text
TRACKER ▸ <project name>
[████░░] <stage_index>/<stage_total> complete
Status: <status>
Stage: <current stage>
Now: <current bounded action>
Evidence: <latest receipt/handoff/checksum>
Blocker: <none or exact blocker>
Next: <next allowed action>
Stop: <stop rule>
```

Rules:

1. First visible line starts with `TRACKER ▸`.
2. Each tracker item is a standalone stacked line.
3. Maximum rendered line width is 64 characters.
4. Visual bar is allowed only when `progress_mode = determinate` and integer `stage_index` and `stage_total` are valid.
5. Indeterminate progress MUST NOT render a percentage or determinate bar.
6. Evidence is required for `DONE` and `BLOCKED` claims.
7. The tracker must remain readable on narrow phone screens when ChatGPT wraps text.

Rationale: User-supplied mobile screenshots from TRACKER-4 showed that box-drawing borders and right-side pipes break under mobile wrapping. The compact stacked format preserves visual status while reflowing as normal text.
