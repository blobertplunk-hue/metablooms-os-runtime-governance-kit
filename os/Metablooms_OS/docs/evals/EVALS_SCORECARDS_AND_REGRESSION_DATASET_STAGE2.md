# Evals Trace Review and Validator Alignment — Stage 2

Stage 2 adds scorecards and a regression dataset for MetaBlooms governance.

## External basis

- Hamel Husain and Shreya Shankar recommend starting evals with error analysis and manual review of representative traces before writing automation.
- OpenAI eval guidance frames evals as: define the task, run test inputs, analyze results, then iterate.
- LangSmith evaluation guidance separates datasets, evaluators, experiments, and trace-linked result analysis.

## Installed artifacts

- `MB_EVALS_SCORECARD_SPEC_v1.json`
- `EVALS_REGRESSION_DATASET_v1.json`
- `EVALS_FAILURE_MODE_CATALOG_v1.json`
- `EVALS_SCORECARD_BASELINE_v1.json`
- `validate_evals_scorecards_stage2_v1.py`

## Operator commands

```bash
mb evals --json
mb evals --check --json
mb evals --scorecards --json
mb evals --regression --json
```

## Promotion rule

Do not claim mature eval coverage unless the regression set has at least 20 reviewed examples, PASS/WARN/BLOCK decisions, repeated failure modes mapped to validators or gates, and a scorecard baseline receipt.
