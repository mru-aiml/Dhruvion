import logging
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base API error with structured response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class UnavailableError(ApiError):
    """Required data or service is unavailable."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__("UNAVAILABLE", message, status_code=503, details=details)


class InvalidInputError(ApiError):
    """Invalid request input."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__("INVALID_INPUT", message, status_code=422, details=details)


class NotFoundError(ApiError):
    """Resource not found."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__("NOT_FOUND", message, status_code=404, details=details)


class UnverifiedError(ApiError):
    """Operation cannot be verified due to missing data."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__("UNVERIFIED", message, status_code=400, details=details)


def create_error_response(
    code: str,
    message: str,
    request_id: str,
    status_code: int,
    details: dict | None = None,
) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "request_id": request_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers."""

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error(
            f"API Error [{request_id}]: {exc.code} - {exc.message}",
            extra={"request_id": request_id, "details": exc.details},
        )
        return create_error_response(
            exc.code, exc.message, request_id, exc.status_code, exc.details
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            f"HTTP Exception [{request_id}]: {exc.status_code} - {exc.detail}",
            extra={"request_id": request_id},
        )
        return create_error_response(
            "HTTP_ERROR",
            str(exc.detail),
            request_id,
            exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            f"Validation Error [{request_id}]: {exc.errors()}",
            extra={"request_id": request_id},
        )
        return create_error_response(
            "INVALID_INPUT",
            "Request validation failed",
            request_id,
            422,
            {"errors": exc.errors()},
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning(
            f"Pydantic Validation Error [{request_id}]: {exc.errors()}",
            extra={"request_id": request_id},
        )
        return create_error_response(
            "INVALID_INPUT",
            "Data validation failed",
            request_id,
            422,
            {"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception(
            f"Unhandled Exception [{request_id}]: {type(exc).__name__}",
            extra={"request_id": request_id},
        )
        return create_error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            request_id,
            500,
        )