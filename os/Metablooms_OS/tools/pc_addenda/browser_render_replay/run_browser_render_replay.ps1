param(
  [Parameter(Mandatory=$true)][string]$HtmlPath,
  [Parameter(Mandatory=$true)][string]$OutDir
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
if (!(Test-Path $HtmlPath)) { throw "HTML file not found: $HtmlPath" }
$pwVersion = $PSVersionTable.PSVersion.ToString()
$meta = [ordered]@{
  tool = 'pc_browser_render_replay_addendum'
  powershell_version = $pwVersion
  html_path = (Resolve-Path $HtmlPath).Path
  out_dir = (Resolve-Path $OutDir).Path
  started_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  screenshots = @()
}
if (!(Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm is required for Playwright PC addendum.' }
Push-Location $OutDir
try {
  if (!(Test-Path package.json)) { npm init -y | Out-Null }
  npm install -D playwright | Out-Null
  npx playwright install chromium | Out-Null
  $script = @"
const {{ chromium, devices }} = require('playwright');
const path = require('path');
(async () => {{
  const htmlPath = process.argv[2];
  const outDir = process.argv[3];
  const fileUrl = 'file:///' + path.resolve(htmlPath).replace(/\\/g, '/');
  const viewports = [
    ['mobile', {{ width: 390, height: 844 }}],
    ['tablet', {{ width: 820, height: 1180 }}],
    ['desktop', {{ width: 1366, height: 768 }}]
  ];
  const browser = await chromium.launch();
  for (const [name, viewport] of viewports) {{
    const page = await browser.newPage({{ viewport }});
    await page.goto(fileUrl);
    await page.screenshot({{ path: path.join(outDir, `${{name}}.png`), fullPage: true }});
    await page.close();
  }}
  await browser.close();
}})().catch(e => {{ console.error(e); process.exit(1); }});
"@
  $scriptPath = Join-Path $OutDir 'playwright_pc_replay.js'
  Set-Content -Path $scriptPath -Value $script -Encoding UTF8
  node $scriptPath (Resolve-Path $HtmlPath).Path (Resolve-Path $OutDir).Path
  foreach ($name in @('mobile','tablet','desktop')) {
    $p = Join-Path $OutDir "$name.png"
    if (!(Test-Path $p)) { throw "Missing screenshot: $p" }
    $meta.screenshots += @{ name=$name; path=(Resolve-Path $p).Path; size_bytes=(Get-Item $p).Length }
  }
  $meta.verdict = 'PASS_FULL_BROWSER_REPLAY'
}
finally { Pop-Location }
$meta.finished_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$meta | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $OutDir 'pc_browser_render_replay_receipt.json') -Encoding UTF8
Write-Output ($meta | ConvertTo-Json -Depth 8)
