# MetaBlooms Operator Surface Quickstart v1

Stage: `IMPLEMENT_UX_OPERATOR_SURFACE_AND_CRITICAL_PATH_SIMPLIFICATION_CARTRIDGE_STAGE_1`  
Created: `20260501T040605Z`

## Critical path

```bash
/mnt/data/Metablooms_OS/bin/mb status
/mnt/data/Metablooms_OS/bin/mb boot --json
/mnt/data/Metablooms_OS/bin/mb verify --json
/mnt/data/Metablooms_OS/bin/mb replay --json
/mnt/data/Metablooms_OS/bin/mb export --output /mnt/data/METABLOOMS_OS_EXPORT.zip --json
```

## Operating rule

The compact CLI is only an operator surface. It does not override governance. A stage is not complete unless validators, receipts, handoffs, and export checks pass.

## UX improvement target

The prior UX/product simplicity score was 1.5/5. Stage 1 raises the evidence-backed score to 2.5/5 by adding a functional command surface plus executable validation. Future stages should add `mb run-stage`, `mb doctor`, and a one-screen tracker preview.
