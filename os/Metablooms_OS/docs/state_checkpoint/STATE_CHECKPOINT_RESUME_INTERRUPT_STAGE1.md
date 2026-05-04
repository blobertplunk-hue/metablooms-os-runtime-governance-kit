# State Checkpoint / Resume / Interrupt Stage 1

Installs canonical thread/checkpoint/interrupt records and `mb checkpoint` commands.

Commands:

```bash
mb checkpoint --stage STAGE --json
mb checkpoint --stage STAGE --interrupt '{"question":"approve?"}' --json
mb checkpoint --resume stage::STAGE --resume-payload '{"decision":"approve"}' --json
mb checkpoint --list --json
```

Stage 2 should wire checkpoints into the stage runner and security interrupts.
