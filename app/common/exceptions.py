from typing import Any, Dict, Optional

class AppException(Exception):
    """Base application exception for mini-wallet backend."""
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class NotFoundException(AppException):
    """Exception raised when a resource is not found (HTTP 404)."""
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details
        )


class BadRequestException(AppException):
    """Exception raised for invalid input or operations (HTTP 400)."""
    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class InsufficientBalanceException(AppException):
    """Exception raised when wallet has insufficient balance (HTTP 400)."""
    def __init__(
        self,
        message: str = "Insufficient balance in wallet",
        error_code: str = "INSUFFICIENT_BALANCE",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class DuplicateRequestException(AppException):
    """Exception raised when an idempotent request is duplicated (HTTP 409)."""
    def __init__(
        self,
        message: str = "Duplicate request or action already performed",
        error_code: str = "DUPLICATE_REQUEST",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details
        )
