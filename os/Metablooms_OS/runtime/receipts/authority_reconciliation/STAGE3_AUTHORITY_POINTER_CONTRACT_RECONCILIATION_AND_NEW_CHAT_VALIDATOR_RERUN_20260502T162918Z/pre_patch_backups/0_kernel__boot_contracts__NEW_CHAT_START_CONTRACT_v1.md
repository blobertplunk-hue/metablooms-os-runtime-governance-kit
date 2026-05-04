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
