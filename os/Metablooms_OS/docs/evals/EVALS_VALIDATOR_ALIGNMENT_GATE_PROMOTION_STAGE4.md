# Evals Stage 4: Validator Alignment Gate Promotion

Stage: `IMPLEMENT_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_STAGE_4_VALIDATOR_ALIGNMENT_GATE_PROMOTION`

This stage promotes eval governance from scorecards and a confusion matrix into an explicit promotion gate.

## Promotion requirements

- At least 20 regression examples.
- PASS/WARN/BLOCK label coverage.
- Accuracy >= 0.90.
- Zero false-pass examples.
- Stage 3 evaluator runner completed.
- Confusion matrix promotion decision is PASS.
- Conservative WARN->BLOCK mismatches are allowed; unsafe WARN/BLOCK->PASS mismatches are blocked.

## Operator commands

```bash
mb evals --alignment-gate --json
mb evals --promotion --json
mb evals --check --json
```

Research basis: practical eval systems should use representative datasets, error analysis, scorecards/evaluators, and regression gates before promotion.
