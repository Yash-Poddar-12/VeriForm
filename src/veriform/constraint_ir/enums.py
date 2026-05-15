from enum import Enum


class CharsetCategory(str, Enum):
    NUMERIC = "numeric"
    ALPHA_UPPER = "alpha_upper"
    ALPHA_LOWER = "alpha_lower"
    ALPHANUMERIC = "alphanumeric"