from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter


def test_default_formatter():
    error = StandardizedError(
        status_code=404,
        code="NOT_FOUND",
        message="Resource not found.",
        trace_id="123",
    )

    formatter = DefaultFormatter()

    result = formatter.format(error)

    assert result["code"] == "NOT_FOUND"
