from playwright.async_api import Page
from typing import List, Dict, Optional

class ValidationObserver:
    """Observes DOM and Network to build ObservationDelta objects deterministically."""
    def __init__(self, page: Page):
        self.page = page

    async def observe_delta(self, baseline_dom: Optional[Dict], current_network: List) -> Dict:
        script = """
        () => {
            const errors = [];
            // Find inputs marked invalid
            document.querySelectorAll('[aria-invalid="true"]').forEach(el => {
                errors.push({ type: 'aria', target: el.id || el.name });
            });
            // Find toast messages (generic class guess for MVP)
            document.querySelectorAll('.toast, .error-message, .alert, .error').forEach(el => {
                const text = el.innerText ? el.innerText.trim() : '';
                // Must be visible
                const style = window.getComputedStyle(el);
                if (text !== '' && style.display !== 'none' && style.visibility !== 'hidden') {
                    errors.push({ type: 'toast', text: text });
                }
            });
            return errors;
        }
        """
        dom_errors = await self.page.evaluate(script)
        import logging
        logging.info(f"[Validation Observer] DOM Extraction complete: {len(dom_errors)} errors found.")
        
        # current_network already contains pre-formatted dicts from sync_manager
        network_errors = current_network
        logging.info(f"[Validation Observer] Network Extraction complete: {len(network_errors)} errors found.")
        
        return {
            "dom_errors": dom_errors,
            "network_errors": network_errors
        }
