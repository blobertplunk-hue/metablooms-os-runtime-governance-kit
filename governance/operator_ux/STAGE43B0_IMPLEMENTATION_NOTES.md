# Stage 43B0 Implementation Notes

This stage installs the first high-level Termux operator command. User-facing commands should now call `metablooms`, not expose raw `gh api`, `jq`, ruleset payload generation, or long shell plumbing.

## Accepted user-facing examples

```bash
metablooms status --pr 8
metablooms merge-pr --pr 8 --expected-head <sha> --stage <stage> --next-stage <stage>
metablooms recover-last-run
metablooms inspect-blocker
```

## Not accepted by default

Long PR-specific scripts that inline ruleset JSON mutation and raw `gh api` calls.
