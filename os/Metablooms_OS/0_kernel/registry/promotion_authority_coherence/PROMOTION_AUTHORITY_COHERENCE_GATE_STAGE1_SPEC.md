# PROMOTION_AUTHORITY_COHERENCE_GATE_STAGE1_SPEC_AND_FIXTURES

Status: SPEC_AND_FIXTURES_DEFINED_NOT_IMPLEMENTED
Created: 2026-05-02T19:59:18.342997+00:00

## Purpose

Prevent a candidate MetaBlooms export from being promoted as current, full-authority, bootable, baseline, or promotion-locked unless the entire authority graph is coherent.

## Gate summary

The gate denies promotion when any controlled artifact is unregistered, any live boot file points to a stale authority, pointer copies disagree, validator CLI contracts are ambiguous or false, fresh-chat replay fails, ZIP contents do not match manifests/ledgers, or receipts claim success without evidence binding.

## Required Stage 2 implementation

Implement `PROMOTION_AUTHORITY_COHERENCE_GATE_v1` as an executable validator, bind it into the export/promotion path before any current-authority pointer update, then run the six fixtures in this stage.

## Fixture coverage

- PAC-FIX-001: unregistered controlled artifact must deny.
- PAC-FIX-002: stale authority in live start file must deny.
- PAC-FIX-003: validator CLI shape mismatch must deny.
- PAC-FIX-004: export manifest missing ZIP member must deny.
- PAC-FIX-005: coherent candidate must pass.
- PAC-FIX-006: success receipt without gate evidence must deny.
