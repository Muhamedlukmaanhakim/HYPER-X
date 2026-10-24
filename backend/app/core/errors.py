from typing import Any, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.core.security import redact_secrets

class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = redact_secrets(message)
        self.status_code = status_code
        self.details = redact_secrets(details) if isinstance(details, str) else details
        super().__init__(self.message)

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": redact_secrets(message),
                "details": exc.detail if not isinstance(exc.detail, str) else None
            }
        }
    )

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": redact_secrets(str(exc))
            }
        }
    )
