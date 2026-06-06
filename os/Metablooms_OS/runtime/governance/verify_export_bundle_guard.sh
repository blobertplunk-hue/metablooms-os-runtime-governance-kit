#!/usr/bin/env bash
set -euo pipefail
BUNDLE=${1:?bundle zip required}
EXPECTED_SHA=${2:-}
[ -f "$BUNDLE" ] || { echo '{"decision":"DENY","reason":"bundle_missing"}'; exit 1; }
unzip -tqq "$BUNDLE" >/dev/null
LIST=$(mktemp)
unzip -Z1 "$BUNDLE" > "$LIST"
grep -Eiq '(baseline|full_os|integrated_os).*\.zip$' "$LIST" || { echo '{"decision":"DENY","reason":"missing_full_baseline_zip"}'; exit 1; }
grep -Eiq '(baseline_pointer|canonical_boot_pointer|current_full_os_baseline_pointer).*\.json$' "$LIST" || { echo '{"decision":"DENY","reason":"missing_pointer"}'; exit 1; }
grep -Eiq '(tracker|control_surface).*\.html$' "$LIST" || { echo '{"decision":"DENY","reason":"missing_tracker"}'; exit 1; }
grep -Eiq '(receipt|lock).*\.json$' "$LIST" || { echo '{"decision":"DENY","reason":"missing_receipt"}'; exit 1; }
grep -Eiq '(manifest|SHA256SUMS|\.sha256$)' "$LIST" || { echo '{"decision":"DENY","reason":"missing_manifest_or_sha"}'; exit 1; }
grep -Eiq '(boot|restore|verify).*(\.py|\.sh|\.md|\.json)$' "$LIST" || { echo '{"decision":"DENY","reason":"missing_boot_restore_evidence"}'; exit 1; }
if [ -n "$EXPECTED_SHA" ]; then
  MATCH=0
  while IFS= read -r f; do
    case "$f" in *.zip) H=$(unzip -p "$BUNDLE" "$f" | sha256sum | awk '{print $1}'); [ "$H" = "$EXPECTED_SHA" ] && MATCH=1 ;; esac
  done < "$LIST"
  [ "$MATCH" = 1 ] || { echo '{"decision":"DENY","reason":"expected_baseline_sha_not_found"}'; exit 1; }
fi
echo '{"decision":"ALLOW","validator":"verify_export_bundle_guard.sh"}'
