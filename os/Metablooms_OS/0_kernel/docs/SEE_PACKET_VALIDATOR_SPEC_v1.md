# SEE_PACKET_VALIDATOR_SPEC_v1

## Purpose

Define the SEE packet schema and validator contract before implementation.

SEE means Search / Evidence / External-research in this runtime. It is the stage that proves research-backed work used `web.run` when required and binds claims to sources.

## Problem being solved

The OS already contains a research trigger rule: if research is required, `web.run` must be used. However, the output of SEE still needs a machine-checkable packet. Without a SEE validator, the system can still claim that research happened without structured evidence, source binding, or contradiction tracking.

## Target schema

`0_kernel/schemas/SEE_PACKET_SCHEMA_v1.json`

## Target validator

`0_kernel/scripts/see_packet_validator_v1.py`

## Required CLI

- `--packet`
- `--packet-file`
- `--schema`
- `--receipt-dir`
- `--json`
- `--strict`

## Required SEE packet sections

### original_request

The request that triggered the SEE pass.

### research_trigger

Must show:

- required = true
- trigger_reason
- trigger_terms

### query_plan

Must list each intended query and purpose.

### web_run_evidence

Must show:

- web_run_called = true
- call_count >= 1
- tool_reference_required = true

### sources

Must include at least one source with:

- source_id
- title
- url_or_ref
- source_type
- used_for

### claim_source_bindings

Must bind every substantive claim to one or more source IDs.

### gaps_and_contradictions

Must separate:

- gaps
- contradictions

### synthesis

Must provide a synthesized conclusion, not merely a source list.

### limitations

Must state uncertainty or limits of the research.

### see_verdict

Must be `PASS` or `FAIL`.

## Hard rule

A SEE packet must fail if it says or implies research happened but does not prove a `web.run` call and source-bound claims.

## Required receipt

The validator writes:

`0_kernel/registry/see_validation_receipts/SEE_VALIDATION_RECEIPT_<timestamp>.json`

Receipt must include:

- packet source;
- schema path;
- schema validation result;
- semantic validation result;
- source-binding validation result;
- web.run evidence validation result;
- verdict;
- issues.

## Return codes

- `0`: validation passes
- `1`: validation fails
- `2`: packet or schema parse failure
- `4`: receipt write failure

## Non-goals

D1 does not:

- implement the validator;
- run SEE;
- call web.run;
- mutate boot routing beyond registry indexing of this spec;
- export a bundle;
- clean `/mnt/data`.

## Required D2 implementation tests

1. Valid full SEE packet passes.
2. Missing `web_run_evidence` fails.
3. `web_run_called = false` fails.
4. Empty `sources` fails.
5. Claim referencing a missing source ID fails.
6. Invalid JSON file fails.
7. Valid packet-file input passes.

## Runaway-turn guard

D1 is specification only. If the stage begins implementation, export, cleanup, or broad filesystem scanning, stop and write a blocked/partial receipt.

## Next Correct Command

`EXECUTE STAGE D2 — SEE PACKET VALIDATOR IMPLEMENTATION`
