import re
from typing import Optional

def normalize_whitespace(text: Optional[str]) -> Optional[str]:
    """Remove extra whitespace, newlines, and tabs from text."""
    if not text:
        return text
    return re.sub(r'\s+', ' ', text).strip()

def normalize_label(label: Optional[str]) -> Optional[str]:
    """Sanitize label text for deterministic matching."""
    if not label:
        return label
    label = normalize_whitespace(label)
    if label:
        # Lowercase, remove trailing colons/asterisks commonly used for required fields
        return label.lower().rstrip(':* ').strip()
    return label

def normalize_attribute(attr: Optional[str]) -> Optional[str]:
    """Normalize HTML attribute values."""
    if not attr:
        return attr
    return attr.strip().lower()

def coerce_bool(val: Optional[str]) -> bool:
    """Coerce HTML boolean attributes (like required='', required='true')."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    val_lower = val.strip().lower()
    return val_lower in {"", "true", "1", "yes", "on"}

def coerce_int(val: Optional[str]) -> Optional[int]:
    """Safely coerce an attribute to int."""
    if val is None or val == "":
        return None
    if isinstance(val, int):
        return val
    try:
        return int(str(val).strip())
    except ValueError:
        return None
