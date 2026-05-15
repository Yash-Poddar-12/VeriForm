from veriform.constraint_ir.enums import CharsetCategory


def test_charset_enum_values():
    assert CharsetCategory.NUMERIC.value == "numeric"
    assert CharsetCategory.ALPHA_UPPER.value == "alpha_upper"
    assert CharsetCategory.ALPHANUMERIC.value == "alphanumeric"