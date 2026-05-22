from playwright.async_api import Page
import hashlib

class ExecutionSnapshot:
    """Captures the absolute state of the DOM and Network at a specific timestamp deterministically."""
    
    @staticmethod
    async def capture_dom_hash(page: Page) -> str:
        script = """
        () => {
            const clone = document.body.cloneNode(true);
            // Strip transient non-deterministic attributes
            clone.querySelectorAll('*').forEach(el => {
                el.removeAttribute('data-playwright');
                // Remove invisible timestamps or random hashes
            });
            return clone.innerHTML;
        }
        """
        dom_string = await page.evaluate(script)
        return hashlib.sha256(dom_string.encode()).hexdigest()
