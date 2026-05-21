"""
veriform.detector.detector
===========================
DOM inspection module.

Responsibilities (Phase 1):
    - Receive a live Playwright ``Page`` object.
    - Locate all ``input[type=text]`` and ``textarea`` elements.
    - Extract HTML5 attributes: name, id, label, required,
      minlength, maxlength, pattern.
    - Return a list of ``FieldSchema`` instances.

Phase 2 extensions:
    - Support email, password, number, date, select.
    - Extract constraints from surrounding label/description text.
"""

from __future__ import annotations

from typing import Any

from veriform.models.schemas import FieldSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


async def detect_fields(page: object, run_id: str) -> list[FieldSchema]:
    """Inspect *page* and return typed metadata for every detectable field.

    Parameters
    ----------
    page:
        A ``playwright.async_api.Page`` instance (typed as ``object`` here so
        the module can be imported without an active Playwright context).
    run_id:
        The parent run identifier – propagated into every ``FieldSchema``.

    Returns
    -------
    list[FieldSchema]
        Detected fields in DOM order.

    """
    controls: list[dict[str, Any]] = await page.evaluate(
        """
        () => {
          const parseOptionalInt = (value) => {
            if (value === null || value === undefined || value === "") return null;
            const parsed = Number.parseInt(value, 10);
            return Number.isFinite(parsed) ? parsed : null;
          };
          const parseOptionalFloat = (value) => {
            if (value === null || value === undefined || value === "") return null;
            const parsed = Number.parseFloat(value);
            return Number.isFinite(parsed) ? parsed : null;
          };
          const inferLabel = (element) => {
            if (!element) return null;
            if (element.id) {
              const explicit = document.querySelector(`label[for="${element.id}"]`);
              if (explicit && explicit.textContent) return explicit.textContent.trim();
            }
            const wrappedLabel = element.closest("label");
            if (wrappedLabel && wrappedLabel.textContent) return wrappedLabel.textContent.trim();
            const aria = element.getAttribute("aria-label");
            return aria ? aria.trim() : null;
          };
          const inferContextText = (element) => {
            if (!element) return null;
            const describedBy = element.getAttribute("aria-describedby");
            if (!describedBy) return null;
            const parts = describedBy
              .split(/\\s+/)
              .map((id) => document.getElementById(id))
              .filter((node) => node && node.textContent)
              .map((node) => node.textContent.trim())
              .filter(Boolean);
            if (parts.length > 0) return parts.join(" ");
            return null;
          };
          const controls = Array.from(
            document.querySelectorAll("input, textarea, select")
          );
          return controls
            .filter((el) => {
              if (el.tagName.toLowerCase() === "input") {
                const inputType = (el.getAttribute("type") || "text").toLowerCase();
                return inputType !== "hidden";
              }
              return true;
            })
            .map((el) => {
              const tag = el.tagName.toLowerCase();
              const inputType = (el.getAttribute("type") || "text").toLowerCase();
              return {
                name: el.getAttribute("name") || el.id || "",
                dom_id: el.id || null,
                type: tag === "input" ? inputType : tag,
                label: inferLabel(el),
                placeholder: el.getAttribute("placeholder"),
                context_text: inferContextText(el),
                required: el.hasAttribute("required"),
                min_length: parseOptionalInt(el.getAttribute("minlength")),
                max_length: parseOptionalInt(el.getAttribute("maxlength")),
                pattern: el.getAttribute("pattern"),
                min_val: parseOptionalFloat(el.getAttribute("min")),
                max_val: parseOptionalFloat(el.getAttribute("max"))
              };
            });
        }
        """
    )

    fields: list[FieldSchema] = []
    for index, control in enumerate(controls, start=1):
        name = str(control.get("name") or "").strip()
        if not name:
            logger.debug("Skipping unnamed control at index=%d", index)
            continue
        fields.append(
            FieldSchema(
                field_id=f"field_{index:03d}",
                run_id=run_id,
                label=_as_optional_str(control.get("label")),
                placeholder=_as_optional_str(control.get("placeholder")),
                context_text=_as_optional_str(control.get("context_text")),
                name=name,
                dom_id=_as_optional_str(control.get("dom_id")),
                type=str(control.get("type") or "text"),
                required=bool(control.get("required", False)),
                min_length=_as_optional_int(control.get("min_length")),
                max_length=_as_optional_int(control.get("max_length")),
                pattern=_as_optional_str(control.get("pattern")),
                min_val=_as_optional_float(control.get("min_val")),
                max_val=_as_optional_float(control.get("max_val")),
            )
        )
    logger.info("detect_fields: extracted %d controls", len(fields))
    return fields


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    stringified = str(value).strip()
    return stringified or None


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
