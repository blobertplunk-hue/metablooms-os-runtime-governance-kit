# MetaBlooms Operator Surface Quickstart v2

Stage: `IMPLEMENT_UX_OPERATOR_SURFACE_AND_CRITICAL_PATH_SIMPLIFICATION_CARTRIDGE_STAGE_2_RUN_STAGE_AND_DOCTOR_COMMANDS`  
Created: `20260501T103500Z`

## Critical path

```bash
/mnt/data/Metablooms_OS/bin/mb status --json
/mnt/data/Metablooms_OS/bin/mb doctor --json
/mnt/data/Metablooms_OS/bin/mb verify --json
/mnt/data/Metablooms_OS/bin/mb run-stage NEXT_STAGE_NAME --dry-run --json
/mnt/data/Metablooms_OS/bin/mb boot --json
/mnt/data/Metablooms_OS/bin/mb export --output /mnt/data/METABLOOMS_OS_EXPORT.zip --json
```

## New Stage 2 behavior

- `doctor` reports diagnostic checks with severity, evidence, and remediation.
- `run-stage` creates a bounded work order by default and does not pretend to execute a stage runner that is not installed.
- `--json` works before or after the subcommand.

## Operating rule

This CLI is an operator surface. It cannot override governance. A stage is complete only when receipts, handoffs, validators, and export checks pass.
