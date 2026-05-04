# MetaBlooms Operator Quickstart v3

Stage 3 adds a checkpointed stage-runner contract and compact tracker preview.

```bash
./bin/mb status
./bin/mb verify --json
./bin/mb doctor --json
./bin/mb tracker
./bin/mb tracker --write --json
./bin/mb run-stage NEXT_STAGE --dry-run --json
./bin/mb run-stage NEXT_STAGE --execute --json
```

`run-stage` still defaults to dry-run. `--execute` validates the work order against `MB_STAGE_RUNNER_CONTRACT_v1` and fails closed unless a real cartridge executor is installed.
