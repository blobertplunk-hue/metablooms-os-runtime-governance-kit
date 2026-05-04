# Sandbox Tool Route Handoff

## Verdict
PASS_WITH_WARNINGS. The current `/mnt/data/Metablooms_OS` root is present and file-count aligned with the ZIP. The OS-native boot executor passed with only `git_dir_missing` warning.

## Working Route
1. `sha256sum -c` the sidecar.
2. `unzip -tq` the archive.
3. `unzip -Z -1` for inventory and critical file checks.
4. Do not delete `/mnt/data/Metablooms_OS` if it already file-count matches the archive.
5. Run boot with `timeout 25s python3 -S /mnt/data/Metablooms_OS/0_kernel/scripts/boot_runtime_executor_v1.py --root /mnt/data/Metablooms_OS`.
6. Accept `PASS_WITH_WARNINGS` only for `git_dir_missing` unless OS artifacts say otherwise.

## Preferred Tools
Use shell/container plus `sha256sum`, `unzip`, `find`, `stat`, `du`, `jq`, and `python3 -S`. Avoid broad normal Python startup and unbounded recursive extraction.

## Next Stage
Run exactly one bounded governed task stage from `/mnt/data/Metablooms_OS`, starting from the latest boot receipt in `0_kernel/registry/boot_receipts/`.
