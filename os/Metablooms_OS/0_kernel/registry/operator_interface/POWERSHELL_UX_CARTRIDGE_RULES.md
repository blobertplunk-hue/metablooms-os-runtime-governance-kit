# MetaBlooms PowerShell UX Cartridge Rules

Status: Stage 23 clean release lock

## Operator workflow

1. Assistant gives one complete PowerShell block.
2. Robert copy/pastes that full block into PowerShell.
3. PowerShell writes a Cyan siren copy-back section.
4. PowerShell writes the same copy-back section to a file.
5. PowerShell copies the copy-back section to clipboard with Set-Clipboard.
6. Robert presses Ctrl+V into ChatGPT.

## Marker standard

- Command headers use solid block markers.
- Paste-back output uses Cyan siren markers.
- Avoid Magenta because it is hard to read.
- White is fallback if Cyan becomes unreadable.

## Interactive PowerShell constraints

- Do not use exit in walkthrough snippets.
- Do not rely on separately pasted finally blocks.
- Avoid nested here-string script generation.
- Avoid zipping a directory containing the active transcript.
- Prefer staged ZIP packaging from a closed copy.
- Always use absolute paths for evidence.
- Use Process-scope Bypass plus recursive Unblock-File for downloaded kits.
- Invoke winget through cmd /c in pipeline-sensitive scripts.
- Normalize GitHub JSON with @() before Where-Object.

## Packaging rule

Evidence packaging should stage evidence into a separate package folder, zip the staged copy, test the ZIP, write SHA-256, and copy the result to clipboard.

