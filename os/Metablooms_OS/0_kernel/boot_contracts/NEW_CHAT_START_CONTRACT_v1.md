# New Chat Start Contract v1

Current authority label: PAC7 full authority export lock.

Bootable full OS authority ZIP:

`/mnt/data/METABLOOMS_OS_PROMOTION_AUTHORITY_COHERENCE_GATE_PAC7_FULL_AUTHORITY_LOCKED_20260502T212700Z.zip`

Required external SHA-256 sidecar:

`/mnt/data/METABLOOMS_OS_PROMOTION_AUTHORITY_COHERENCE_GATE_PAC7_FULL_AUTHORITY_LOCKED_20260502T212700Z.zip.sha256`

Canonical working root after extraction:

`/mnt/data/Metablooms_OS`

Mandatory gates before work:

- Verify the authority ZIP SHA-256 using the external sidecar.
- `runtime/governance/boot_critical_governance_loader_v1.py`
- `runtime/governance/governance_scatter_prevention_v1.py`
- `runtime/governance/fresh_chat_boot_rehearsal_v1.py`
- `runtime/governance/new_chat_start_contract_validator_v1.py`
- `runtime/cartridges/prompt_governance_v1/validate_prompt_governance_cartridge_v1.py`
- `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json`
- `0_kernel/mpp_v3/promotion_authority_coherence_gate_v1.py --root /mnt/data/Metablooms_OS --report-current`
- `0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json`

Promotion rule: no future export may be called current, full authority, bootable, baseline, promotion-locked, or latest without a passing `PROMOTION_AUTHORITY_COHERENCE_GATE_v1` result.
