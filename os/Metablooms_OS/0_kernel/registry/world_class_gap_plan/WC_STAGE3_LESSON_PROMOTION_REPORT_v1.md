# WC Stage 3 — Lesson Promotion Queue and Fixture Factory

Status: PASS pending export verification.

## Purpose
Convert repeated workflow lessons into durable OS behavior, promotion queue records, and regression fixtures.

## Accepted lessons

- **LESSON_EXPORT_LINK_PRECHECK_001** — download_link_exposure_failure: Never publish a download link until the exact ZIP and sidecar pass stat, hash check, ZIP integrity, and clean extraction/boot smoke where applicable.
- **LESSON_FULL_AUTHORITY_DEFAULT_002** — missing_delta_authority: After each successful governed stage, prefer a short-name bootable full authority export over requiring the operator to preserve a chain of deltas.
- **LESSON_STAGE_EXIT_PROMPT_003** — operator_cognitive_load: Every stage handoff must include a copy-ready next prompt that references the latest verified short-name boot authority.
- **LESSON_PHONE_SAFE_FILENAMES_004** — mobile_download_friction: Publish short phone-safe aliases for primary boot authorities and checksums; preserve long provenance names only as internal metadata.
- **LESSON_BOOT_MANIFEST_LOCATION_005** — authority_manifest_path_ambiguity: Boot authority manifest lookup must support the OS-root manifest and registry mirror, and exports should include both to avoid path ambiguity.
- **LESSON_RECONSTRUCTION_PROVENANCE_006** — lost_artifact_reconstruction: Rebuilt authorities must be labeled as reconstructed and must not be represented as original lost artifacts.

## External grounding
- Google SRE postmortem practice: preventive action items should reduce recurrence.
- Atlassian retrospective practice: teams should identify what worked, what failed, and actionable improvements.

## Next stage
WC_STAGE6_GENERAL_CAPABILITY_RESOLVER_FRAMEWORK
