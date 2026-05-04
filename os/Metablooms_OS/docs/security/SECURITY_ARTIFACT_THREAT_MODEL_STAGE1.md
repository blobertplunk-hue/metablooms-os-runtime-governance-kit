# Security Artifact Threat Model Stage 1

Installs a machine-readable threat model, trust policy, validator, and `mb security` operator command.

Primary risks: prompt injection, stale authority, unsafe archive paths, excessive agency, insecure output handling, resource exhaustion, unverifiable receipts, and sensitive data disclosure.

Commands:

```bash
mb security --json
mb security --check --json
mb trace --status ERROR --json
```
