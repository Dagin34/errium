from rest_framework.exceptions import ErrorDetail

from errium_drf.normalizers import flatten_drf_errors


def test_flatten_simple_field_errors():
    detail = {
        "email": [ErrorDetail("Enter a valid email address.", code="invalid")],
        "password": [ErrorDetail("This field is required.", code="required")],
    }
    result = flatten_drf_errors(detail)
    assert result == {
        "email": "Enter a valid email address.",
        "password": "This field is required.",
    }


def test_flatten_nested_serializer_errors():
    detail = {
        "address": {"city": [ErrorDetail("This field is required.", code="required")]},
    }
    result = flatten_drf_errors(detail)
    assert result == {"address.city": "This field is required."}


def test_flatten_non_field_errors():
    detail = [ErrorDetail("Passwords do not match.", code="invalid")]
    result = flatten_drf_errors(detail)
    assert result == {"non_field_errors": "Passwords do not match."}


def test_flatten_multiple_messages_for_one_field_are_joined():
    detail = {
        "password": [
            ErrorDetail("Too short.", code="min_length"),
            ErrorDetail("Must contain a digit.", code="invalid"),
        ]
    }
    result = flatten_drf_errors(detail)
    assert result == {"password": "Too short. Must contain a digit."}


def test_flatten_list_serializer_many_errors():
    detail = [
        {},
        {"email": [ErrorDetail("This field is required.", code="required")]},
    ]
    result = flatten_drf_errors(detail)
    assert result == {"1.email": "This field is required."}
