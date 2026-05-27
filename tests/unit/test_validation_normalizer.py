from errium_core.normalizers.validation import ValidationNormalizer


def test_field_required_mapping():
    # Pydantic v2 missing error representation
    errors = [{"type": "missing", "loc": ["body", "password"], "msg": "Field required"}]
    normalizer = ValidationNormalizer()
    normalized = normalizer.normalize(errors)

    assert "password" in normalized
    assert normalized["password"] == "Password is required."


def test_email_formatting_errors():
    errors = [
        {
            "type": "value_error.email",
            "loc": ["body", "email"],
            "msg": "value is not a valid email",
        }
    ]
    normalizer = ValidationNormalizer()
    normalized = normalizer.normalize(errors)

    assert "email" in normalized
    assert normalized["email"] == "Invalid email format."


def test_multiple_field_errors():
    errors = [
        {"type": "missing", "loc": ["body", "password"], "msg": "Field required"},
        {
            "type": "value_error.email",
            "loc": ["body", "email"],
            "msg": "value is not a valid email",
        },
        {
            "type": "value_error",
            "loc": ["body", "profile", "age"],
            "msg": "none is not an allowed value",
        },
    ]
    normalizer = ValidationNormalizer()
    normalized = normalizer.normalize(errors)

    assert "password" in normalized
    assert normalized["password"] == "Password is required."

    assert "email" in normalized
    assert normalized["email"] == "Invalid email format."

    # Nested path check
    assert "profile.age" in normalized
    assert normalized["profile.age"] == "Value cannot be empty."


def test_custom_mappings():
    errors = [{"type": "too_short", "loc": ["body", "username"], "msg": "Too short"}]
    # Initialize with custom templates
    normalizer = ValidationNormalizer(
        custom_mappings={"too_short": "{field_name} must be at least 5 chars."}
    )
    normalized = normalizer.normalize(errors)

    assert "username" in normalized
    assert normalized["username"] == "Username must be at least 5 chars."
