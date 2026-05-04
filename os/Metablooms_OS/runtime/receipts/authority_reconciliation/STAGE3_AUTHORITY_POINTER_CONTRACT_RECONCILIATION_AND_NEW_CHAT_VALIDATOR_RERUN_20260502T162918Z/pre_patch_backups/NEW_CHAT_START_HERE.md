# MetaBlooms OS Start Here

<!-- METABLOOMS_OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_v1 -->

## Operator visual tracker first

Open the visual tracker before governed work resumes:

```text
OPEN_OPERATOR_VISUAL_TRACKER.html
runtime/operator_tracker/operator_visual_tracker_latest.html
runtime/operator_tracker/OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_LATEST.json
```

Current rule: show the tracker first, then execute exactly one bounded governed stage.

Latest full authority from this stage is verified by external `.sha256` sidecar because a ZIP cannot contain its own final hash without changing its bytes.

Current repaired full authority export: `METABLOOMS_OS_OPERATOR_VISUAL_TRACKER_POLISH_STAGE3_FULL_AUTHORITY_REPAIRED_20260502T154025Z.zip`
Checksum sidecar: `METABLOOMS_OS_OPERATOR_VISUAL_TRACKER_POLISH_STAGE3_FULL_AUTHORITY_REPAIRED_20260502T154025Z.zip.sha256`

---

# MetaBlooms OS Start Contract — Stage 12 Pointer Promotion

Authority ZIP: `METABLOOMS_OS_PROMPT_GOVERNANCE_CARTRIDGE_INSTALL_12_POINTER_PROMOTION_AND_RUNTIME_STARTER_SMOKE_FULL_AUTHORITY_20260501T010500Z.zip`
Sidecar: `METABLOOMS_OS_PROMPT_GOVERNANCE_CARTRIDGE_INSTALL_12_POINTER_PROMOTION_AND_RUNTIME_STARTER_SMOKE_FULL_AUTHORITY_20260501T010500Z.zip.sha256`

Required startup sequence:
1. Verify sidecar SHA-256 before trusting the archive.
2. Treat `/mnt/data/Metablooms_OS` as the canonical working root after extraction or targeted boot.
3. Run boot-required governance gates.
4. Run `runtime/governance/runtime_starter_smoke_v1.py` for targeted starter proof.
5. Run prompt route pre-execution enforcement before substantive MetaBlooms work.
6. Write a receipt and handoff for every bounded stage.

Fail closed if checksum verification, boot-required file checks, scatter governance, prompt cartridge validation, pre-execution routing, or runtime starter smoke cannot be proven.
