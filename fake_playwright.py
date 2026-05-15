"""Deterministic fake Playwright-like page objects for unit/integration tests."""

from __future__ import annotations

import re
from pathlib import Path


class FakePage:
    def __init__(self, controls: list[dict[str, object]]) -> None:
        self._controls = controls
        self.url = "about:blank"
        self.validation_message: str | None = None
        self._last_field_name: str | None = None
        self._last_value: str = ""

    async def goto(self, url: str, timeout: int | None = None) -> None:
        _ = timeout
        self.url = url
        self.validation_message = None

    async def evaluate(self, script: str):
        _ = script
        return self._controls

    def locator(self, selector: str) -> "FakeLocator":
        return FakeLocator(self, selector)

    async def wait_for_load_state(self, state: str, timeout: int | None = None) -> None:
        _ = (state, timeout)
        return None

    async def screenshot(self, path: str, full_page: bool = True) -> None:
        _ = full_page
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_bytes(b"fake-image")

    def _record_fill(self, selector: str, value: str) -> None:
        self._last_field_name = _field_name_from_selector(selector)
        self._last_value = value

    def _submit(self) -> None:
        if self._last_field_name is None:
            self.validation_message = "No field selected"
            return

        semantic = _semantic_from_field_name(self._last_field_name)
        is_valid = _is_valid_value(semantic, self._last_value)
        if is_valid:
            self.url = f"{self.url.rstrip('/')}/success"
            self.validation_message = None
            return

        self.validation_message = f"Invalid value for {semantic}"


class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self._page = page
        self._selector = selector

    @property
    def first(self) -> "FakeLocator":
        return self

    async def fill(self, value: str) -> None:
        self._page._record_fill(self._selector, value)

    async def click(self, timeout: int | None = None) -> None:
        _ = timeout
        if "submit" in self._selector:
            self._page._submit()

    async def press(self, key: str) -> None:
        if key == "Enter":
            self._page._submit()

    async def inner_text(self, timeout: int | None = None) -> str:
        _ = timeout
        validation_selectors = {
            "[role='alert']",
            ".error",
            ".invalid",
            ".validation-error",
            "[aria-invalid='true']",
        }
        if self._selector not in validation_selectors:
            raise RuntimeError("No text for selector")
        if self._page.validation_message is None:
            raise RuntimeError("No validation message")
        return self._page.validation_message


def _field_name_from_selector(selector: str) -> str:
    if selector.startswith("#"):
        return selector[1:]
    match = re.search(r"\[name=['\"](?P<name>[^'\"]+)['\"]\]", selector)
    if match:
        return match.group("name")
    return selector


def _semantic_from_field_name(field_name: str) -> str:
    lowered = field_name.lower()
    if "mobile" in lowered or "phone" in lowered:
        return "mobile_number"
    if "loan" in lowered and "account" in lowered:
        return "loan_account_number"
    if "dob" in lowered or ("date" in lowered and "birth" in lowered):
        return "date_of_birth"
    if "application" in lowered or "reference" in lowered:
        return "application_reference_number"
    return "generic_text"


def _is_valid_value(semantic: str, value: str) -> bool:
    if semantic == "mobile_number":
        return value.isdigit() and len(value) == 10
    if semantic == "loan_account_number":
        return value.isdigit() and 8 <= len(value) <= 16
    if semantic == "date_of_birth":
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)) and value < "2025-01-01"
    if semantic == "application_reference_number":
        return value.isalnum() and 6 <= len(value) <= 20
    return bool(value)
