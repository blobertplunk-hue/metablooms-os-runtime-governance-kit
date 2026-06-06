# G5_BUNDLE_AUDIT_LESSONS_LEARNED_v1

## Source

`/mnt/data/Pasted markdown.md`

## Main conclusion

The G5 repaired export is much stronger than F7, but it is still a **near-pass**, not a final baseline lock, until the validator decision path ambiguity is fixed.

## Learned invariants

1. If an export manifest declares a path like `0_kernel/registry/...`, that file must exist inside the main ZIP at that path.
2. If a proof/validator decision is external-only, the manifest must use an explicit external artifact locator and sidecar binding, not an internal-looking path.
3. After a repaired export validates, update `CURRENT_WORKING_BASELINE_POINTER_v1.json` to the latest validated lifecycle stage or mark it intentionally stale/non-authoritative.
4. Add an explicit DAG-to-ledger mapping artifact. Do not infer that DAG short IDs match ledger full IDs.
5. A cryptographically verified governance bundle proves the governance layer, but does not prove main-bundle self-consistency.
6. A near-pass export with external governance proof still requires main-bundle self-consistency before baseline lock.

## Open repair targets

- BUG: G5 validator decision declared as internal-looking path but missing from G5 main ZIP.
- WARN: pointer still reflects F7-era stage/head.
- WARN: DAG/ledger ID mapping layer missing.

## Positive learning

The governance bundle pattern worked: manifest + SHA sidecar + file-level hashes created the strongest governance export so far.

## Next Correct Command

`EXECUTE G6 — RECOVERY PROOF + BASELINE LOCK WITH G5 AUDIT OPEN ISSUES`
