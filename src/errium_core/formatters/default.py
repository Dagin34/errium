from errium_core.contracts.error import StandardizedError


class DefaultFormatter:
    def format(
        self,
        error: StandardizedError,
    ) -> dict:
        return {
            "success": False,
            "status": error.status_code,
            "code": error.code,
            "message": error.message,
            "trace_id": error.trace_id,
            "timestamp": error.timestamp.isoformat(),
            "details": error.details,
        }
