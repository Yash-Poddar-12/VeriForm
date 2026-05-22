import json

class PlaywrightScriptGenerator:
    """Compiles a serialized replay sequence into a standalone Playwright Python script."""
    
    @staticmethod
    def generate(sequence_json: str, output_path: str):
        sequence = json.loads(sequence_json)
        script = [
            "import asyncio",
            "from playwright.async_api import async_playwright",
            "",
            "async def run():",
            "    async with async_playwright() as p:",
            "        browser = await p.chromium.launch(headless=False)",
            "        context = await browser.new_context()",
            "        page = await context.new_page()",
            ""
        ]
        
        for step in sequence:
            if step["action"] == "goto":
                script.append(f'        await page.goto("{step["url"]}")')
            elif step["action"] == "fill":
                script.append(f'        await page.locator("{step["selector"]}").fill("{step["value"]}")')
            elif step["action"] == "click":
                script.append(f'        await page.locator("{step["selector"]}").click()')
                
        script.extend([
            "        await page.wait_for_timeout(2000) # Wait for observation",
            "        await browser.close()",
            "",
            "if __name__ == '__main__':",
            "    asyncio.run(run())"
        ])
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\\n".join(script))
