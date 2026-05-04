# MANIFEST_PROVENANCE_EXPORT_CONTRACT_v1

## Purpose

Make every future export restorable, verifiable, and explainable.

## Required export artifacts

Each export must produce:

1. external sidecar SHA-256 manifest
2. internal `EXPORT_MANIFEST_v1.json`
3. internal `EXPORT_PROVENANCE_v1.json`
4. internal `RESTORE_CONTRACT_v1.json`
5. internal `CAPABILITY_SET_v1.json`

## Why this matters

A ZIP alone is not enough. A valid stable ZIP can still be stale, and a missing sidecar manifest can block recovery. The ZIP must contain internal provenance while also writing an external sidecar manifest.

## Required manifest fields

- export file name
- SHA-256
- size in bytes
- source root
- source Git HEAD
- clean-tree status
- capability set
- excluded path policy
- provenance reference
- restore contract reference
- verdict

## Required provenance fields

- builder identity
- source Git commit and branch
- materials: pointer, ledger, DAG, boot manifest, artifact registry
- recipe: export command/policy
- subject: exported ZIP and hash
- capability set
- verification summary

## Restore requirements

Future restore must:

1. verify sidecar manifest or explicit manifest-repair receipt;
2. extract into staging;
3. set `git config core.filemode false`;
4. verify required capabilities;
5. promote only after staging validation passes.

## F4 non-goals

F4 does not export, run recovery proof, or implement restore ladder.

## Next Correct Command

`EXECUTE F5 — RESTORE LADDER + MODE-NORMALIZATION PROOF`
