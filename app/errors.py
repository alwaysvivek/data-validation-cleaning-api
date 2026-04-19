"""Structured error classes and FastAPI exception handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base error
# ---------------------------------------------------------------------------
class APIError(Exception):
    """Base class for all API errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(message)

    def to_response(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "detail": self.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Concrete errors
# ---------------------------------------------------------------------------
class FileTooLargeError(APIError):
    status_code = 413
    error_code = "FILE_TOO_LARGE"

    def __init__(self, max_bytes: int, received_bytes: int):
        super().__init__(
            message=f"File exceeds {max_bytes // (1024 * 1024)}MB limit",
            detail={"max_bytes": max_bytes, "received_bytes": received_bytes},
        )


class UnsupportedFileTypeError(APIError):
    status_code = 422
    error_code = "UNSUPPORTED_FILE_TYPE"

    def __init__(self, extension: str, allowed: set[str]):
        super().__init__(
            message=f"File type '{extension}' is not supported",
            detail={"received": extension, "allowed": sorted(allowed)},
        )


class EmptyDatasetError(APIError):
    status_code = 422
    error_code = "EMPTY_DATASET"

    def __init__(self):
        super().__init__(message="The uploaded dataset contains no data rows")


class ProcessingError(APIError):
    status_code = 500
    error_code = "PROCESSING_ERROR"

    def __init__(self, message: str = "An error occurred while processing the data"):
        super().__init__(message=message)


class AIServiceUnavailableError(APIError):
    status_code = 503
    error_code = "AI_SERVICE_UNAVAILABLE"

    def __init__(self):
        super().__init__(
            message="AI service is unavailable. Set GROQ_API_KEY in environment.",
        )


# ---------------------------------------------------------------------------
# Register handlers on the FastAPI app
# ---------------------------------------------------------------------------
def register_error_handlers(app: FastAPI) -> None:
    """Attach structured error handlers to the application."""

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        logger.warning("API error %s: %s", exc.error_code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        body = {
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "detail": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(status_code=500, content=body)
