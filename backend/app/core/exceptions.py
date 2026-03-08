from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with HTTP status code and detail message."""

    def __init__(self, status_code: int = 500, detail: str = "An unexpected error occurred"):
        """Initialize with status code and detail message."""
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)


class NotFoundException(AppException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, detail: str = "Resource not found"):
        """Initialize with 404 status code."""
        super().__init__(status_code=404, detail=detail)


class UnauthorizedException(AppException):
    """Exception raised when authentication fails or is missing."""

    def __init__(self, detail: str = "Unauthorized"):
        """Initialize with 401 status code."""
        super().__init__(status_code=401, detail=detail)


class BadRequestException(AppException):
    """Exception raised when the request is malformed or invalid."""

    def __init__(self, detail: str = "Bad request"):
        """Initialize with 400 status code."""
        super().__init__(status_code=400, detail=detail)


class ConflictException(AppException):
    """Exception raised when there is a resource conflict."""

    def __init__(self, detail: str = "Conflict"):
        """Initialize with 409 status code."""
        super().__init__(status_code=409, detail=detail)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle AppException instances and return a structured JSON error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
