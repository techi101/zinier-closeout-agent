# Playwright check: console errors, failed requests, horizontal overflow, fonts, screenshots at 1440 and 390.
# Usage: python check_page.py <url> <outdir> [--full]
import sys, json, pathlib
from playwright.sync_api import sync_playwright

url, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
full = "--full" in sys.argv
report = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--mute-audio"])
    for w, h in [(1440, 900), (390, 844)]:
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg = ctx.new_page()
        errs, failed = [], []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("requestfailed", lambda r: failed.append(r.url))
        pg.on("response", lambda r: failed.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_timeout(4500)
        pg.screenshot(path=str(out / f"hero_{w}.png"))
        if full: pg.screenshot(path=str(out / f"full_{w}.png"), full_page=True)
        info = pg.evaluate("""async () => { await document.fonts.ready;
          const fams = ['Cabinet Grotesk','Switzer','JetBrains Mono'].map(f => [f, document.fonts.check('16px "'+f+'"')]);
          return {overflow: document.documentElement.scrollWidth - window.innerWidth,
                  fonts: Object.fromEntries(fams), text: document.body.innerText.length,
                  h1: getComputedStyle(document.querySelector('h1')).fontFamily,
                  recFilled: document.querySelectorAll('#rec .val.in').length}; }""")
        report[w] = dict(console_errors=errs, failed_requests=failed, **info)
        ctx.close()
    b.close()
print(json.dumps(report, indent=1))
