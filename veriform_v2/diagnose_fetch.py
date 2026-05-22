"""
Minimal isolated diagnostic: proves whether the page JS fetch fires at all,
and whether Playwright response listeners capture it.
Run WHILE the benchmark server is up on port 8000.
"""
import asyncio
from playwright.async_api import async_playwright

async def diagnose():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        captured_requests = []
        captured_responses = []

        # Sync lambda listeners — confirmed compatible with page.on()
        page.on("request", lambda r: captured_requests.append(r.url))
        page.on("response", lambda r: captured_responses.append((r.url, r.status)))

        print("Navigating to benchmark page...")
        await page.goto("http://127.0.0.1:8000/optimistic_ui.html")
        await page.wait_for_load_state("domcontentloaded")

        print("Filling INVALID PAN (length 9 to trigger fetch)...")
        await page.locator("#pan").fill("ABCDE1234")

        print("Clicking submit button...")
        btn = page.locator("#btn")
        count = await btn.count()
        print(f"Button found: {count}")
        await btn.click()

        print("Waiting 2000ms for setTimeout(500ms) to fire...")
        await page.wait_for_timeout(2000)

        print(f"\nAll captured requests ({len(captured_requests)}):")
        for url in captured_requests:
            print(f"  REQUEST: {url}")

        print(f"\nAll captured responses ({len(captured_responses)}):")
        for url, status in captured_responses:
            print(f"  RESPONSE: {status} {url}")

        # Also check JS console for errors
        print("\nEvaluating JS directly to check button click state:")
        toast_visible = await page.locator("#toast").is_visible()
        print(f"  Toast visible after click: {toast_visible}")

        pan_len = await page.evaluate("() => document.getElementById('pan').value.length")
        print(f"  PAN field value length: {pan_len}")

        await browser.close()

asyncio.run(diagnose())
