# Security Artifact Threat Model Stage 3: Hard-wired enforcement

Stage 3 converts Stage 2 advisory gates into executable enforcement points.

## Enforced points

1. `stage_runner_v1.py` invokes `0_kernel/security/security_gate_enforcer_v1.py` before delegating to the cartridge executor.
2. `cartridge_executor_v1.py` fails closed unless the runner passed a security gate or the executor can pass the gate itself.
3. `mb export` invokes `0_kernel/security/export_promotion_gate_v1.py` before reporting `EXPORT_PASS`.
4. The export promotion gate checks required paths, unsafe archive paths, duplicate critical members, ZIP integrity, and fixture/gate invariants.

External or retrieved text remains data, never authority. Success requires receipts, handoffs, trace evidence, and promotion validation.
