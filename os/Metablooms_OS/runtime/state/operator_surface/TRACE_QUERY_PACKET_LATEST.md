# Trace Query Packet

- Stage: `OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE12_TRACE_QUERY_PACKET_AND_SEARCHABLE_EVIDENCE_INDEX`
- Verdict: `PASS`
- Index: `runtime/traces/observability/SEARCHABLE_EVIDENCE_INDEX_LATEST.json`
- Rebuilt UTC: `20260502T181724Z`

## Blocker evidence
Find blocker/failure evidence and repair route.

Query: `blocked blocker error failure repair router`
Results: `8`

- `runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json` — score `11`
- `runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json` — score `9`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl` — score `7`
- `runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json` — score `6`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE5_TRACE_INGESTION_CLASSIFIER_REPAIR_AND_REGRESSION_FIXTURES_20260502T165923Z/STAGE_RECEIPT.json` — score `6`

## Stage evidence
Find stage receipts, validations, and handoffs.

Query: `stage validation receipt handoff verdict pass fail`
Results: `8`

- `runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl` — score `413`
- `runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json` — score `140`
- `runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json` — score `54`
- `runtime/traces/observability/MB_TRACE_STAGE2_SUMMARY_STDOUT_LATEST.json` — score `32`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/stage9_validator.json` — score `18`

## Export proof
Find export containment and hash evidence.

Query: `export containment proof zip sha256 duplicate members required artifacts`
Results: `8`

- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/stage9_validator.json` — score `147`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE8_HISTORICAL_CALLSITE_QUARANTINE_VALIDATION_LATEST.json` — score `143`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE10_BOOT_SURFACE_MINIMAL_MODE_AND_MOBILE_RENDER_HARDENING_FINALIZED_20260502T175839Z/STAGE10_FINALIZATION_BLOCKED.json` — score `143`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/stage8_validator.json` — score `141`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_VALIDATION_LATEST.json` — score `140`

## Boot path
Find current boot guidance and wrapper validation.

Query: `live boot guidance wrapper root new chat validator allow`
Results: `8`

- `runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json` — score `79`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl` — score `78`
- `runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json` — score `24`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/stage9_validator.json` — score `15`
- `runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.md` — score `14`

## Tracker surface
Find tracker UI evidence.

Query: `operator tracker minimal mode visual waterfall evidence filters`
Results: `8`

- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/NEW_CHAT_START_HERE.md` — score `14`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE7_METHOD_WRAPPER_CALLSITE_RETROFIT_AND_BOOT_SEQUENCE_ENFORCEMENT_20260502T170919Z/pre_patch_backups/NEW_CHAT_START_HERE.md` — score `12`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE8_BOOT_RECEIPT_WRAPPER_ONLY_ENFORCEMENT_AND_HISTORICAL_CALLSITE_QUARANTINE_20260502T171707Z/pre_patch_backups/NEW_CHAT_START_HERE.md` — score `12`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/0_kernel__boot_contracts__NEW_CHAT_START_CONTRACT_v1.md` — score `8`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE10_BOOT_SURFACE_MINIMAL_MODE_AND_MOBILE_RENDER_HARDENING_20260502T175629Z/CE_SYNTHESIS.json` — score `8`

## Callsite quarantine
Find historical/live callsite classification evidence.

Query: `historical callsite quarantine direct runtime starter smoke wrapper only`
Results: `8`

- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/0_kernel__boot_contracts__NEW_CHAT_START_CONTRACT_v1.md` — score `21`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/NEW_CHAT_START_HERE.md` — score `17`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE8_BOOT_RECEIPT_WRAPPER_ONLY_ENFORCEMENT_AND_HISTORICAL_CALLSITE_QUARANTINE_20260502T171707Z/pre_patch_backups/0_kernel__boot_contracts__NEW_CHAT_START_CONTRACT_v1.md` — score `14`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/0_kernel__registry__current_authority__CURRENT_FULL_AUTHORITY_POINTER_v1.json` — score `12`
- `runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS_20260502T174908Z/pre_patch_backups/CURRENT_FULL_AUTHORITY_POINTER_v1.json` — score `12`

