from datetime import UTC, datetime

from errium_core.config.settings import ErriumSettings, set_settings
from errium_core.contracts.error import StandardizedError
from errium_core.formatters.default import DefaultFormatter


def test_default_formatter_production_mode():
    # Force production mode
    set_settings(ErriumSettings(debug=False))

    error = StandardizedError(
        status_code=404,
        code="RESOURCE_NOT_FOUND",
        message="Resource not found.",
        trace_id="trace-12345",
        success=False,
    )

    formatter = DefaultFormatter()
    result = formatter.format(error)

    # Standardized output structure checks
    assert result["success"] is False
    assert result["status_code"] == 404
    assert result["code"] == "RESOURCE_NOT_FOUND"
    assert result["message"] == "Resource not found."
    assert result["trace_id"] == "trace-12345"
    assert "timestamp" in result
    assert result["details"] is None
    # Traceback should be hidden in production
    assert "debug" not in result


def test_default_formatter_production_500_sanitization():
    # Force production mode
    set_settings(ErriumSettings(debug=False))

    error = StandardizedError(
        status_code=500,
        code="DATABASE_CRASHED",
        message="SQL syntax error near SELECT * FROM secret_table",
        trace_id="trace-500",
        success=False,
    )

    formatter = DefaultFormatter()
    result = formatter.format(error)

    # In production, internal server errors (>= 500) must be sanitized!
    assert result["status_code"] == 500
    assert result["code"] == "INTERNAL_SERVER_ERROR"
    assert result["message"] == "An unexpected error occurred."
    assert "debug" not in result


def test_default_formatter_debug_mode():
    # Force debug mode
    set_settings(ErriumSettings(debug=True))

    raw_exc = ValueError("Database crashed")
    try:
        raise raw_exc
    except ValueError as exc:
        error = StandardizedError(
            status_code=500,
            code="DATABASE_ERROR",
            message="Internal database error.",
            trace_id="trace-debug",
            success=False,
            exception=exc,
        )

    formatter = DefaultFormatter()
    result = formatter.format(error)

    # In debug mode:
    # 1. Message and code are NOT sanitized
    assert result["status_code"] == 500
    assert result["code"] == "DATABASE_ERROR"
    assert result["message"] == "Internal database error."

    # 2. Debug info is included with class name, exception message, and stack trace
    assert "debug" in result
    debug_info = result["debug"]
    assert debug_info["exception"] == "ValueError"
    assert debug_info["message"] == "Database crashed"
    assert "ValueError: Database crashed" in debug_info["stack_trace"]
    assert len(debug_info["hints"]) > 0
    assert (
        "An internal database or backend logic error occurred."
        in debug_info["hints"][0]
    )


def test_timestamp_and_trace_id_correctness():
    trace_id = "trace-uuid-example"
    now = datetime.now(UTC)
    error = StandardizedError(
        status_code=400,
        code="BAD_REQUEST",
        message="Bad request.",
        trace_id=trace_id,
        timestamp=now,
    )

    formatter = DefaultFormatter()
    result = formatter.format(error)

    assert result["trace_id"] == trace_id
    assert result["timestamp"] == now.isoformat()
