from fastapi.responses import JSONResponse
from scrapper_service.presentation.http.schemas.responses import ApiErrorResponse


def error_response(
    status_code: int,
    description: str,
    code: str,
    exc: Exception | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        description=description,
        code=code,
        exceptionName=exc.__class__.__name__ if exc else "",
        exceptionMessage=str(exc) if exc else "",
        stacktrace=[],
    ).model_dump(exclude_none=True)

    return JSONResponse(status_code=status_code, content=body)
