# EVAL-0 Governance Regression Suite

Status: PASS

Built a shell-first regression suite for known MetaBlooms governance failures.

- Total cases: 10
- Passing smoke runner cases: 10
- Normal Python used: false

## Regression classes covered

1. Tiny bundle mistaken for full OS
2. Normal Python canary leak
3. Missing web.run on governance repair
4. Missing pre-tool contract
5. Zero-byte receipt
6. Tracker contradiction
7. Bad SHA sidecar
8. Unbounded command
9. ACSM resume without manifest hash
10. Positive valid governed context

## Next stage

EVAL-1 PROMOTE GOVERNANCE_REGRESSION_SUITE_v1 THROUGH GPC
