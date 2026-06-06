# MetaBlooms OS — New Chat Start Here

Current boot authority: **WC13 repaired2 full bootable authority export**.

Authoritative ZIP:

`/mnt/data/METABLOOMS_WC13_FINAL_BOOTABLE_FULL_AUTHORITY_REPAIRED2_20260503T232000Z.zip`

SHA-256 sidecar:

`/mnt/data/METABLOOMS_WC13_FINAL_BOOTABLE_FULL_AUTHORITY_REPAIRED2_20260503T232000Z.zip.sha256`

Authority status:

- WC13 final export: created and replay-proven in Stage 30.
- WC13 root authority repair: Stage 31 repaired stale root narrative/identity files and removed root write-probe debug artifacts.
- WC13 contains the WC12 bootable OS continuation plus Stage23 PC/GitHub automation kit authorities, GitHub governance/release pointers, streaming-safe execution policy, paste-back/clipboard UX rules, and Stage 26–30 WC13 integration receipts.

Required start sequence:

1. Verify `METABLOOMS_WC13_FINAL_BOOTABLE_FULL_AUTHORITY_REPAIRED2_20260503T232000Z.zip` against `METABLOOMS_WC13_FINAL_BOOTABLE_FULL_AUTHORITY_REPAIRED2_20260503T232000Z.zip.sha256`.
2. Extract or verify `/mnt/data/Metablooms_OS` from the ZIP root `Metablooms_OS/`.
3. Read this file, `BOOT_AUTHORITY_MANIFEST_v1.json`, `EXPORT_MANIFEST_v1.json`, and `BOOT_HANDOFF_WC13.md` as the current root boot identity.
4. Open/show `OPEN_OPERATOR_VISUAL_TRACKER.html` when useful.
5. Run `portable_full_os_boot_verify.py` before governed work.
6. Execute at most one bounded governed stage, then write receipt and handoff.

Fail closed if the ZIP/sidecar is missing, the SHA-256 does not match, the portable boot verifier fails, or any root authority file references an older authority as current.

Allowed claim:

> WC13 repaired2 bootable OS export exists, root authority narrative is current, and replay proof passed.

Disallowed claims until future stages prove them:

- Failing PRs are blocked.
- PR review is required.
- CODEOWNERS is enforced.
- Force-push/delete protection has been behavior-tested.
- Full professional repo governance is complete.
