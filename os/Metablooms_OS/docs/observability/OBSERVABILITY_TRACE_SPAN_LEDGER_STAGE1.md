# Observability Trace/Span Ledger Stage 1

Installs a canonical JSONL trace/span ledger and extends `mb trace` with filters and summary writing.

Commands:

```bash
mb trace --json
mb trace --stage IMPLEMENT_OBSERVABILITY_TRACE_SPAN_LEDGER_CARTRIDGE_STAGE_1 --json
mb trace --status ERROR --json
mb trace --write-summary --json
```

The canonical ledger is `runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl`. Every span must include schema_version, trace_id, span_id, parent_span_id, name, stage_name, event, status, timestamp_utc, and attributes. Invalid JSONL, missing IDs, or ERROR/BLOCKED spans without error/blocker/reason attributes block an observability pass.
