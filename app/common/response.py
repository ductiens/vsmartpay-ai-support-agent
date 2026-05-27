from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Return a unified success API JSON response.
    
    Response format:
    {
        "success": True,
        "message": "Success",
        "data": ...
    }
    """
    content = {
        "success": True,
        "message": message,
        "data": data
    }
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=headers
    )


def error_response(
    message: str,
    error_code: str,
    status_code: int = 400,
    details: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Return a unified error API JSON response.
    
    Response format:
    {
        "success": False,
        "error_code": "ERROR_CODE",
        "message": "User-friendly message",
        "details": ...
    }
    """
    content = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details or {}
    }
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        headers=headers
    )
