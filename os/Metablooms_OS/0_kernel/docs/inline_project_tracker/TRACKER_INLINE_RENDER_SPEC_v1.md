# TRACKER_INLINE_RENDER_SPEC_v1

Status: design locked; implementation pending.

## Default compact renderer

Use this at the very top of every governed project turn:

```text
╭─ PROJECT TRACKER ─────────────────────────╮
│ Project: <project_name>                    │
│ Status: <UNBOOTED/BOOTING/RUNNING/...>     │
│ Stage: <stage_id or current phase>         │
│ Progress: <N/M, bar, or indeterminate>     │
│ Now: <current bounded action>              │
│ Evidence: <receipt/handoff/path/hash>      │
│ Blocker: <none or exact blocker>           │
│ Next: <next allowed action>                │
│ Stop Rule: <bounded stop condition>        │
╰───────────────────────────────────────────╯
```

## Determinate progress rule

Allowed when all are true:

- `stage_index` is known.
- `stage_total` is known.
- `stage_total > 0`.
- `stage_index <= stage_total`.
- The denominator comes from an artifact-backed DAG, checklist, or explicit user stage list.

Format:

```text
Progress: █████░░░░░ 5/10
```

## Indeterminate progress rule

Use this when denominator is unknown:

```text
Progress: active; denominator not artifact-proven
```

Do not show a percent or filled bar in indeterminate mode.

## Blocked state renderer

```text
╭─ PROJECT TRACKER ─────────────────────────╮
│ Project: <project_name>                    │
│ Status: BLOCKED                            │
│ Stage: <stage_id>                          │
│ Progress: stopped at blocker               │
│ Now: no execution                          │
│ Evidence: <blocking receipt path/hash>     │
│ Blocker: <exact blocker>                   │
│ Next: <only allowed recovery action>       │
│ Stop Rule: fail closed                     │
╰───────────────────────────────────────────╯
```

## Done state renderer

```text
╭─ PROJECT TRACKER ─────────────────────────╮
│ Project: <project_name>                    │
│ Status: DONE                               │
│ Stage: <final stage id>                    │
│ Progress: complete <N/N if known>          │
│ Now: no active execution                   │
│ Evidence: <final receipt/export/hash>      │
│ Blocker: none                              │
│ Next: optional smoke audit or new project  │
│ Stop Rule: closed                          │
╰───────────────────────────────────────────╯
```

## Required future artifacts

Implementation should create, in a later stage:

- `TRACKER_STATE_SCHEMA_v1.json`
- `TRACKER_STATE_v1.json`
- `TRACKER_RENDERER_v1.*`
- `TRACKER_VALIDATOR_v1.*`
- `TRACKER_BOOT_GATE_v1.md`
- `TRACKER_STAGE_GATE_v1.md`
- `TRACKER_EVIDENCE_BINDING_v1.md`
- `TRACKER_HANDOFF_UPDATE_v1.md`

## Non-implementation boundary

TRACKER-0 does not create a cartridge, validator executable, runtime hook, or enforcement patch. It only locks the research-backed design and next implementation plan.
