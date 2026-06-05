# Old Chat GitHub Registration Cartridge

Purpose: let an old chat register its URL and claimed work, compare those claims against a GitHub repository manifest, and emit a fail-closed report identifying work that is already shared, missing, duplicated, or still needs promotion.

This cartridge deliberately separates **registration** from **promotion**. It does not push old-chat work automatically. It produces a deterministic report that tells the operator what still needs to be shared.

## Inputs

1. Old-chat packet: a JSON object containing the chat URL, source chat identifier, and one or more claimed artifacts.
2. GitHub repository manifest: a JSON object listing repository files with path, SHA-256 digest, and byte size.

## Output

A comparison report with registered chat URL, duplicate URL status, per-artifact verdicts, unshared artifacts, missing local evidence, and already-shared matches by path or SHA-256.

## Fail-closed rules

- Missing or malformed chat URL fails validation.
- Missing artifact digest and path fails validation.
- A GitHub manifest marked `truncated: true` fails comparison.
- Duplicate chat URLs are flagged and must be reconciled before promotion.
- Digest conflicts are not silently resolved.
