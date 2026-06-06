# MetaBlooms Live Boot Guidance

Stage: `OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS`

## Current live steps only

1. **Verify authority pointer and external sidecar.**  
   `CURRENT_FULL_AUTHORITY_POINTER_v1.json + external .sha256 sidecar`  
   Evidence: `CURRENT_FULL_AUTHORITY_POINTER_v1.json`
2. **Open the operator tracker before work resumes.**  
   `OPEN_OPERATOR_VISUAL_TRACKER.html`  
   Evidence: `OPEN_OPERATOR_VISUAL_TRACKER.html`
3. **Run boot-critical governance loader.**  
   `python runtime/governance/boot_critical_governance_loader_v1.py`  
   Evidence: `runtime/governance/boot_critical_governance_loader_v1.py`
4. **Run scatter prevention and fresh-chat rehearsal.**  
   `python runtime/governance/governance_scatter_prevention_v1.py && python runtime/governance/fresh_chat_boot_rehearsal_v1.py`  
   Evidence: `runtime/governance/fresh_chat_boot_rehearsal_v1.py`
5. **Validate the new-chat start contract.**  
   `python runtime/governance/new_chat_start_contract_validator_v1.py /mnt/data/Metablooms_OS`  
   Evidence: `runtime/governance/new_chat_start_contract_validator_v1.py`
6. **Run runtime starter smoke through the wrapper only.**  
   `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json`  
   Evidence: `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py`
7. **Validate historical-callsite quarantine and live boot guidance.**  
   `python 0_kernel/validators/validate_observability_trace_span_ledger_stage8_historical_callsite_quarantine_v1.py --root /mnt/data/Metablooms_OS --json && python 0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py --root /mnt/data/Metablooms_OS --json`  
   Evidence: `0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py`
8. **Execute exactly one bounded governed stage, then write receipt and handoff.**  
   `stage-specific governed command`  
   Evidence: `runtime/receipts/`

## Deep links

- [Operator tracker](OPEN_OPERATOR_VISUAL_TRACKER.html) — `OPEN_OPERATOR_VISUAL_TRACKER.html`
- [Live boot guidance JSON](runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json) — `runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json`
- [Live boot guidance Markdown](runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.md) — `runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.md`
- [New-chat contract](0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md) — `0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md`
- [Historical quarantine index](runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json) — `runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json`
- [Stage 9 validator](0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py) — `0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py`
