# Observability Trace/Span Ledger Stage 2

Stage ID: `OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE2_UNIFIED_EVENT_SCHEMA_AND_BOOT_INGESTION`

## Purpose

Stage 2 upgrades the Stage 1 trace ledger from a raw span list into a normalized event/provenance substrate. It adds:

- canonical trace/span event schema: `0_kernel/registry/observability/MB_TRACE_SPAN_EVENT_SCHEMA_v1.json`
- causal graph schema: `0_kernel/registry/observability/MB_CAUSAL_STAGE_GRAPH_SCHEMA_v1.json`
- boot ingestion spec: `0_kernel/registry/observability/MB_OBSERVABILITY_BOOT_INGESTION_SPEC_v1.json`
- bounded ingestion script: `0_kernel/scripts/observability_boot_ingest_v1.py`
- validator: `0_kernel/validators/validate_observability_trace_span_ledger_stage2_v1.py`

## Canonical outputs

- `runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json`
- `runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json`
- `runtime/traces/observability/BOOT_INGESTION_REPORT_LATEST.json`
- `runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE2_VALIDATION_LATEST.json`

## Governance contract

The raw JSONL ledger is canonical. Indexes, summaries, graph views, and tracker previews are derivative artifacts and must be regenerated from the raw ledger.

Failure conditions:

1. invalid JSONL
2. missing canonical fields
3. unknown parent span references
4. ERROR/BLOCKED records without `attributes.error`, `attributes.blocker`, or `attributes.reason`
5. index/graph count mismatch with raw ledger
6. missing schemas, script, validator, or canonical outputs

## Operator commands

```bash
python3 -S 0_kernel/scripts/observability_boot_ingest_v1.py --root /mnt/data/Metablooms_OS --json
python3 -S 0_kernel/validators/validate_observability_trace_span_ledger_stage2_v1.py --root /mnt/data/Metablooms_OS --write-report --json
bin/mb trace --write-summary --json
```

## Integration value

This stage creates the substrate for later tracker polish, CDR/MPP trace analysis, export provenance, recovery replay, evaluator alignment, and failure clustering.
