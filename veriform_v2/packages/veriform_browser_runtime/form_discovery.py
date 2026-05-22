from playwright.async_api import Page
from typing import List, Dict

class FormDiscovery:
    """Scans the DOM deterministically to find interactive form fields."""
    def __init__(self, page: Page):
        self.page = page
        
    async def discover_fields(self) -> List[Dict]:
        script = """
        () => {
            const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select'));
            return inputs.map(el => {
                let labelText = '';
                if (el.id) {
                    const label = document.querySelector(`label[for="${el.id}"]`);
                    if (label) labelText = label.innerText;
                }
                return {
                    id: el.id,
                    name: el.name,
                    tagName: el.tagName.toLowerCase(),
                    type: el.type,
                    label: labelText,
                    placeholder: el.placeholder || '',
                    required: el.required || false,
                    ariaInvalid: el.getAttribute('aria-invalid'),
                    autocomplete: el.getAttribute('autocomplete')
                };
            }).filter(i => i.id || i.name); // Ignore purely anonymous inputs for now
        }
        """
        return await self.page.evaluate(script)
