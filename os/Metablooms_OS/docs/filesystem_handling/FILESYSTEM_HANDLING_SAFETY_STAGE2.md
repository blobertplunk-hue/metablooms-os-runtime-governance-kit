# Filesystem Handling Safety Stage 2

Stage: `HARD_WIRE_FILESYSTEM_SAFETY_INTO_ALL_EXPORT_AND_EXTRACTION_ROUTES_STAGE_2`

## Hard-wired behavior

- `mb export` now writes the archive and sidecar to temp files in the destination directory and checks `df -P` mount point plus `st_dev` before `os.replace`.
- `mb extract` publishes only from a destination-parent staging directory after archive preflight, required-root checks, final-byte finalization marker, and same-mount publication preflight.
- Export promotion blocks unsafe paths, duplicate critical entries, missing filesystem safety proof, and partial/in-progress root markers.
- Differential logging stores full manifests as artifacts while trace output is bounded to root hashes, delta counts, and sample paths.

## Operator examples

```bash
mb export --output /mnt/data/METABLOOMS_OS_EXPORT.zip --json
mb extract --archive /mnt/data/METABLOOMS_OS_EXPORT.zip --dest /mnt/data/Metablooms_OS --replace --json
mb fs-safety --json
```
