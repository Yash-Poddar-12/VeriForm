"""
veriform.detector.detector
===========================
DOM inspection module.

Responsibility (Phase 2):
- Extract observable DOM metadata using a lightweight JS payload.
- No inference or business logic in the browser context.
- Python handles normalization and deterministic semantic classification.
"""

from __future__ import annotations

from typing import Any

from veriform.models.schemas import FieldSchema
from veriform.utils.logging import get_logger
from veriform.detector.normalization import (
    normalize_label, normalize_whitespace, normalize_attribute,
    coerce_bool, coerce_int
)
from veriform.detector.semantic_classifier import SemanticClassifier

logger = get_logger(__name__)


async def detect_fields(page: object, run_id: str) -> list[FieldSchema]:
    """Inspect *page* and return typed metadata for every detectable field."""
    
    # Lightweight JS extraction
    controls: list[dict[str, Any]] = await page.evaluate(
        """
        () => {
          const inferLabel = (element) => {
            if (!element) return null;
            if (element.id) {
              const explicit = document.querySelector(`label[for="${element.id}"]`);
              if (explicit && explicit.textContent) return explicit.textContent;
            }
            const wrappedLabel = element.closest("label");
            if (wrappedLabel && wrappedLabel.textContent) return wrappedLabel.textContent;
            return element.getAttribute("aria-label");
          };
          
          const inferContextText = (element) => {
            if (!element) return null;
            const describedBy = element.getAttribute("aria-describedby");
            if (!describedBy) return null;
            return describedBy
              .split(/\\s+/)
              .map(id => document.getElementById(id))
              .filter(n => n && n.textContent)
              .map(n => n.textContent)
              .join(" ");
          };
          
          const findValidationContainers = (element) => {
              const containers = [];
              const errId = element.getAttribute("aria-errormessage");
              if (errId) {
                  const errNode = document.getElementById(errId);
                  if (errNode && errNode.textContent) containers.push(errNode.textContent);
              }
              // Check immediate siblings for error classes
              let sibling = element.nextElementSibling;
              while(sibling) {
                  if (sibling.className && typeof sibling.className === 'string' && sibling.className.toLowerCase().includes('error')) {
                      if (sibling.textContent) containers.push(sibling.textContent);
                  }
                  sibling = sibling.nextElementSibling;
              }
              return containers;
          };

          const controls = Array.from(document.querySelectorAll("input, textarea, select"));
          
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
              return {
                name: el.getAttribute("name") || el.id || "",
                dom_id: el.id || null,
                type: el.getAttribute("type") || (tag === "input" ? "text" : tag),
                label: inferLabel(el),
                placeholder: el.getAttribute("placeholder"),
                context_text: inferContextText(el),
                required: el.hasAttribute("required") ? "true" : el.getAttribute("required"),
                minlength: el.getAttribute("minlength"),
                maxlength: el.getAttribute("maxlength"),
                pattern: el.getAttribute("pattern"),
                min_val: el.getAttribute("min"),
                max_val: el.getAttribute("max"),
                autocomplete: el.getAttribute("autocomplete"),
                inputmode: el.getAttribute("inputmode"),
                readonly: el.hasAttribute("readonly") ? "true" : el.getAttribute("readonly"),
                disabled: el.hasAttribute("disabled") ? "true" : el.getAttribute("disabled"),
                aria_invalid: el.getAttribute("aria-invalid"),
                aria_required: el.getAttribute("aria-required"),
                title: el.getAttribute("title"),
                validation_message_containers: findValidationContainers(el)
              };
            });
        }
        """
    )

    fields: list[FieldSchema] = []
    skipped = 0
    classified_count = 0

    for index, control in enumerate(controls, start=1):
        name = normalize_whitespace(control.get("name"))
        if not name:
            skipped += 1
            logger.debug("Skipping unnamed control at index=%d", index)
            continue
            
        # Normalize attributes in Python
        norm_metadata = {
            "name": name,
            "dom_id": normalize_whitespace(control.get("dom_id")),
            "type": normalize_attribute(control.get("type")),
            "label": normalize_label(control.get("label")),
            "placeholder": normalize_whitespace(control.get("placeholder")),
            "context_text": normalize_whitespace(control.get("context_text")),
            "autocomplete": normalize_attribute(control.get("autocomplete")),
            "inputmode": normalize_attribute(control.get("inputmode")),
            "pattern": control.get("pattern"),
            "title": normalize_whitespace(control.get("title")),
            "aria_invalid": normalize_attribute(control.get("aria_invalid")),
            "aria_required": normalize_attribute(control.get("aria_required")),
        }
        
        # Classification
        sem_type, conf, signals = SemanticClassifier.classify(norm_metadata)
        if sem_type:
            classified_count += 1
            if conf < 0.5:
                logger.debug(f"Ambiguous classification for field {name}: {sem_type} (conf: {conf})")
        
        # Clean validation messages
        raw_msgs = control.get("validation_message_containers") or []
        clean_msgs = [normalize_whitespace(m) for m in raw_msgs if m]
        
        fields.append(
            FieldSchema(
                field_id=f"field_{index:03d}",
                run_id=run_id,
                
                # Base metadata
                name=norm_metadata["name"],
                dom_id=norm_metadata["dom_id"],
                type=norm_metadata["type"] or "text",
                label=norm_metadata["label"],
                placeholder=norm_metadata["placeholder"],
                context_text=norm_metadata["context_text"],
                
                # HTML constraints
                required=coerce_bool(control.get("required")),
                min_length=coerce_int(control.get("minlength")),
                max_length=coerce_int(control.get("maxlength")),
                pattern=norm_metadata["pattern"],
                min_val=_as_optional_float(control.get("min_val")),
                max_val=_as_optional_float(control.get("max_val")),
                
                # New Discovery attributes
                autocomplete=norm_metadata["autocomplete"],
                inputmode=norm_metadata["inputmode"],
                readonly=coerce_bool(control.get("readonly")),
                disabled=coerce_bool(control.get("disabled")),
                aria_invalid=norm_metadata["aria_invalid"],
                aria_required=norm_metadata["aria_required"],
                title=norm_metadata["title"],
                validation_message_containers=clean_msgs,
                
                # Semantics
                semantic_type=sem_type,
                semantic_confidence=conf,
                matched_signals=signals
            )
        )

    logger.info("detect_fields: extracted %d controls | skipped %d | classified %d", 
                len(fields), skipped, classified_count)
                
    return fields


def _as_optional_float(value: Any) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
