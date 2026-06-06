from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    page=b.new_page(viewport={'width':390,'height':844})
    page.goto('file:///mnt/data/Metablooms_OS/OPEN_OPERATOR_VISUAL_TRACKER.html')
    page.screenshot(path='/mnt/data/Metablooms_OS/runtime/receipts/browser_render_capability_resolver/BROWSER_RENDER_CAPABILITY_RESOLVER_STAGE2_IMPLEMENT_RESOLVER_AND_LOCAL_METHOD_REPLAY_20260502T224609Z/local_replay/playwright_probe.png', full_page=True)
    b.close()
