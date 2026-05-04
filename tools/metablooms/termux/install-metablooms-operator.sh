#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/bin"
mkdir -p "$DEST"
cp "$SRC_DIR/metablooms" "$DEST/metablooms"
chmod +x "$DEST/metablooms"
case ":$PATH:" in *":$DEST:"*) ;; *) echo "Add this to ~/.bashrc if needed: export PATH=\"$DEST:\$PATH\"";; esac
"$DEST/metablooms" status --repo blobertplunk-hue/metablooms-os-runtime-governance-kit --pr 8 || true
