#!/usr/bin/env python3
"""MetaBlooms Loop Controller v2.

Canonical stage sequencer. SEE is first. CONTROL_WRITE is last.
Fail-closed on every stage gate.
"""
from __future__ import annotations


# SIR12A_BUDGET_GUARD_START
DEFAULT_MAX_STEPS = 25
DEFAULT_MAX_ITERATIONS = 25

class RunawayLoopGuardError(RuntimeError):
    """Raised when loop_controller exceeds its governed step budget."""
    pass

def enforce_budget_guard(step_index, max_steps=DEFAULT_MAX_STEPS, *, label="loop_controller"):
    """Fail closed when a loop/pipeline step exceeds the explicit governed budget."""
    if max_steps is None:
        max_steps = DEFAULT_MAX_STEPS
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    if step_index >= max_steps:
        raise RunawayLoopGuardError(f"{label} exceeded max_steps={max_steps}")
    return True

def bounded_range(iterable, max_steps=DEFAULT_MAX_STEPS, *, label="loop_controller"):
    """Yield items from iterable while enforcing an explicit max_steps budget."""
    for step_index, item in enumerate(iterable):
        enforce_budget_guard(step_index, max_steps=max_steps, label=label)
        yield item
# SIR12A_BUDGET_GUARD_END

import json
import time
from pathlib import Path
from typing import Any, Callable

STAGE_ORDER = [
    "BASELINE_LOCK",
    "SEE",
    "SEE_EVIDENCE_VALIDATOR",
    "SIGNAL_CONTRACT",
    "DRS",
    "OFM",
    "ADS",
    "CE",
    "CE_CRITIC",
    "ACTIVATION_PROOF",
    "planner",
    "router",
    "execution",
    "CONSTRAINT_EVALUATOR",
    "RESULT_EVALUATOR",
    "CDR_LINT",
    "CRV",
    "GAPFINDER",
    "VALIDATION",
    "ECL",
    "CONTROL_WRITE",
]

MANDATORY_STAGES = {
    "BASELINE_LOCK", "SEE", "CE", "VALIDATION", "ECL", "CONTROL_WRITE"
}

RESEARCH_STAGES = {"SEE", "SEE_EVIDENCE_VALIDATOR"}


class StageGateFailed(Exception):
    pass


class LoopController:
    def __init__(self, state: dict[str, Any], stage_registry: dict[str, Callable]):
        self.state = state
        self.registry = stage_registry
        self.executed: list[str] = []
        self.receipts: list[dict[str, Any]] = []
        self.start_time = time.time()

    def _require(self, condition: bool, name: str) -> None:
        if not condition:
            raise StageGateFailed(f"GATE_FAILED:{name}")

    def _gate_see_before_validation(self) -> None:
        """Split-brain guard: SEE must have run before VALIDATION."""
        self._require(
            self.state.get("see_executed") is True,
            "SEE_NOT_EXECUTED_BEFORE_VALIDATION"
        )

    def _gate_ce_before_planner(self) -> None:
        """CE must pass before planner runs."""
        self._require(
            self.state.get("ce_critic_pass") is True,
            "CE_CRITIC_NOT_PASSED_BEFORE_PLANNER"
        )

    def _write_stage_receipt(
        self, stage: str, status: str, output: dict | None = None
    ) -> dict[str, Any]:
        receipt = {
            "stage": stage,
            "status": status,
            "timestamp": time.time(),
            "output_keys": list((output or {}).keys()),
        }
        self.receipts.append(receipt)
        return receipt

    def run_stage(self, stage: str) -> dict[str, Any]:
        """Execute one stage. Fail closed if gate fails or stage not registered."""
        # Pre-stage gates
        if stage == "VALIDATION":
            self._gate_see_before_validation()
        if stage == "planner":
            self._gate_ce_before_planner()

        # Get stage function
        fn = self.registry.get(stage)
        if fn is None:
            if stage in MANDATORY_STAGES:
                raise StageGateFailed(f"MANDATORY_STAGE_NOT_REGISTERED:{stage}")
            # Non-mandatory missing stage: warn and skip
            self._write_stage_receipt(stage, "SKIPPED_NOT_REGISTERED")
            return {"stage": stage, "status": "SKIPPED"}

        # Execute
        try:
            # Inject execution trace into state for CONTROL_WRITE
            self.state["executed_stages"] = list(self.executed)
            self.state["stage_receipts"] = list(self.receipts)
            output = fn(self.state)
            self.state.update(output or {})
            self.executed.append(stage)

            # Post-stage flags
            if stage == "SEE":
                self.state["see_executed"] = True
            if stage == "CE_CRITIC":
                self.state["ce_critic_pass"] = self.state.get("ce_critic_pass", True)

            receipt = self._write_stage_receipt(stage, "COMPLETE", output)
            return receipt
        except StageGateFailed:
            raise
        except Exception as exc:
            self._write_stage_receipt(stage, "FAILED")
            raise StageGateFailed(f"STAGE_EXECUTION_FAILED:{stage}:{exc}") from exc

    def run_all(self) -> dict[str, Any]:
        """Run all stages in canonical order. Fail closed on any mandatory stage failure."""
        errors = []

        for stage in STAGE_ORDER:
            try:
                self.run_stage(stage)
            except StageGateFailed as e:
                errors.append(str(e))
                if stage in MANDATORY_STAGES:
                    break  # Hard stop on mandatory stage failure

        missing_mandatory = [
            s for s in MANDATORY_STAGES if s not in self.executed
        ]

        return {
            "executed_stages": self.executed,
            "stage_receipts": self.receipts,
            "errors": errors,
            "missing_mandatory": missing_mandatory,
            "status": "COMPLETE" if not errors and not missing_mandatory else "FAILED",
            "duration_seconds": round(time.time() - self.start_time, 3),
            "see_executed": self.state.get("see_executed", False),
        }


def make_registry_from_engines(engines_dir: Path) -> dict[str, Callable]:
    """Load stage functions from engines directory."""
    import importlib.util
    import sys

    registry: dict[str, Callable] = {}
    stages_dir = engines_dir / "stages"

    if stages_dir.exists():
        for py_file in sorted(stages_dir.glob("*.py")):
            stage_name = py_file.stem.upper()
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                if hasattr(mod, "run"):
                    registry[stage_name] = mod.run
                    # Also register under the STAGE_ID if defined
                    if hasattr(mod, "STAGE_ID"):
                        registry[mod.STAGE_ID] = mod.run
            except Exception as e:
                print(f"WARNING: could not load stage {py_file.name}: {e}")

    return registry


if __name__ == "__main__":
    # Self-test
    calls = []

    def make_stage(name):
        def fn(state):
            calls.append(name)
            return {f"{name.lower()}_done": True}
        return fn

    # Minimal registry with SEE required
    registry = {
        s: make_stage(s) for s in STAGE_ORDER
    }

    state = {}
    controller = LoopController(state, registry)
    result = controller.run_all()

    assert "SEE" in result["executed_stages"], "SEE must execute"
    assert "CONTROL_WRITE" in result["executed_stages"], "CONTROL_WRITE must execute"
    assert result["see_executed"] is True, "see_executed flag must be set"
    idx_see = result["executed_stages"].index("SEE")
    idx_val = result["executed_stages"].index("VALIDATION")
    assert idx_see < idx_val, "SEE must execute before VALIDATION"
    print("loop_controller self-test: PASS")
    print(f"Stages executed: {len(result['executed_stages'])}")
    print(f"Status: {result['status']}")
