import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.common.exceptions import AppException
from app.common.response import error_response
from app.config import settings

logger = logging.getLogger(__name__)

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return error_response(
            message=exc.message,
            error_code=exc.error_code,
            status_code=exc.status_code,
            details=exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        return error_response(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=exc.errors()
        )

    from fastapi import HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        # Translate FastAPI's HTTPException to our standard error response
        error_code = "HTTP_ERROR"
        if exc.status_code == 401:
            error_code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            error_code = "FORBIDDEN"
        elif exc.status_code == 404:
            error_code = "NOT_FOUND"
        elif exc.status_code == 400:
            error_code = "BAD_REQUEST"
            
        return error_response(
            message=str(exc.detail),
            error_code=error_code,
            status_code=exc.status_code
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        if settings.DEBUG:
            return error_response(
                message=str(exc),
                error_code="INTERNAL_SERVER_ERROR",
                status_code=500
            )
        return error_response(
            message="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
