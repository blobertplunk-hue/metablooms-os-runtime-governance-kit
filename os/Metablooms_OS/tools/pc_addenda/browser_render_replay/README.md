# Browser Render Replay PC Addendum

This addendum is optional. MetaBlooms visual workflows are sandbox-first for Android + ChatGPT `/mnt/data` work.

Use this only when a PC/PowerShell 7 environment is available and you want stronger true-browser evidence than the sandbox could produce.

## Purpose

- Install or verify Playwright managed Chromium.
- Replay the same HTML render target used by the sandbox resolver.
- Produce desktop/tablet/mobile PNG screenshots plus metadata.
- Do not override sandbox evidence; append stronger evidence as an enhancement.

## Standard command

```powershell
pwsh ./run_browser_render_replay.ps1 -HtmlPath "OPEN_OPERATOR_VISUAL_TRACKER.html" -OutDir "runtime/render_replay_pc"
```

## Governance rule

A PC pass may upgrade `honesty_label` from `sandbox_render_proxy` to `full_browser_replay`, but a missing PC run must not block ordinary Android-phone sandbox workflows unless the artifact explicitly declares `browser_screenshot_required`.
