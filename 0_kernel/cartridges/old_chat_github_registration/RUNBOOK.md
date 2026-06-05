# Old Chat GitHub Registration Runbook

## Stage 1: Intake

Ask the old chat to provide a packet using `mb.old_chat_github_registration.packet.v1`.

Required fields:

- `chat_url`
- `source_chat_id`
- `artifacts[]`

Each artifact must include at least a `declared_path` or a `sha256`.

## Stage 2: Manifest source selection

Use the strongest available GitHub manifest:

1. Complete repository manifest artifact from GitHub Actions.
2. Connector-generated manifest snapshot.
3. Targeted path/digest probes, marked as incomplete.

If the manifest is truncated, stop.

## Stage 3: Comparison

Run:

```bash
python3 0_kernel/cartridges/old_chat_github_registration/tools/old_chat_github_registration.py \
  --packet OLD_CHAT_PACKET.json \
  --manifest GITHUB_MANIFEST.json \
  --out REPORT.json
```

## Stage 4: Decisions

- `ALREADY_SHARED_BY_PATH_AND_SHA`: no action needed.
- `ALREADY_SHARED_BY_SHA_DIFFERENT_PATH`: record alias/path drift.
- `PATH_PRESENT_SHA_MISMATCH`: review before overwrite.
- `UNSHARED`: candidate for promotion.
- `MISSING_LOCAL_EVIDENCE`: ask old chat for export/artifact.

## Stage 5: Promotion

Promotion is separate. The cartridge emits evidence; it does not push unreviewed files.
