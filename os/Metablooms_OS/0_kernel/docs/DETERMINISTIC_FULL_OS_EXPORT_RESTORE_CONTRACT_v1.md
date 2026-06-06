# Deterministic Full OS Export Restore Contract v1

This contract permanently addresses two restore hazards:

1. **Double wrapper**: a wrapped archive already contains `Metablooms_OS/`; restoring it into a same-named root creates a nested runtime root.
2. **Partial extraction promotion**: a timed-out or interrupted extraction must not expose or replace a boot root.

## Required restore behavior

Use the canonical restore tool:

```bash
python3 -S tools/metablooms/restore_full_os_archive_v1.py \
  --archive /path/to/METABLOOMS_FULL_OS_EXPORT.tar.zst \
  --extract-parent /mnt/data \
  --receipt /mnt/data/metablooms_restore_receipt.json \
  --print-summary
```

## Forbidden restore shape

Do not restore a wrapped export into a destination whose basename is already `Metablooms_OS`. The archive wrapper would become nested under the existing root.

## Promotion rule

The live root is replaced only after staging extraction passes archive integrity, member listing, wrapper layout, required boot members, and shell syntax validation.

## Top-level archive policy

The wrapper directory `Metablooms_OS/` is required. The only permitted sibling top-level artifacts are export metadata such as `MANIFEST.json`, `MANIFEST.sha256`, and `EXPORT_RECEIPT.json`. Any other sibling blocks restore.
