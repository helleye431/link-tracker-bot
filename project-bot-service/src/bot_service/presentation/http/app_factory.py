from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from prometheusrock import PrometheusMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware

from bot_service.presentation.http.routers.updates_router import update_router
from bot_service.application.services.update_service import UpdateService
from bot_service.presentation.http.schemas.responses import ApiErrorResponse
from bot_service.presentation.http.lifespan import build_lifespan
from bot_service.presentation.http.utils.rate_limiter import (
    rate_limiter,
    limiter_period,
)


def create_app(
    title: str,
    version: str,
    contact_name: str,
    contact_url: str,
    update_service: UpdateService,
    request_limit: int,
    request_limit_period: limiter_period,
) -> FastAPI:
    """
    Создаёт и настраивает FastAPI-приложение bot-сервиса.

    Подключает роутеры, lifespan и глобальные обработчики ошибок
    """
    limiter = rate_limiter(
        request_limit=request_limit, request_limit_period=request_limit_period
    )

    lifespan = build_lifespan(update_service=update_service, limiter=limiter)

    app = FastAPI(
        title=title,
        version=version,
        contact={
            "name": contact_name,
            "url": contact_url,
        },
        lifespan=lifespan,
    )

    app.include_router(update_router)
    app.add_middleware(SlowAPIASGIMiddleware)
    app.add_middleware(
        PrometheusMiddleware,
        app_name="bot",
        skip_paths=["/metrics"],
        remove_labels=["headers"],
    )

    # очистка автоматической ошибки 422 fastapi в openapi
    def custom_openapi():
        if not app.openapi_schema:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )
            for _, method_item in app.openapi_schema.get("paths").items():
                for _, param in method_item.items():
                    responses = param.get("responses")

                    if "422" in responses:
                        del responses["422"]
        return app.openapi_schema

    setattr(app, "openapi", custom_openapi)

    # на всякий случай обработка validation fastapi ошибки
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, exc: RequestValidationError):
        body = ApiErrorResponse(
            description="Некорректные параметры запроса",
            code="BAD_REQUEST",
            exceptionName=exc.__class__.__name__,
            exceptionMessage=str(exc),
        ).model_dump(exclude_none=True)

        return JSONResponse(status_code=400, content=body)

    # обработка ошибки rate limit
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(_, exc: RateLimitExceeded):
        body = ApiErrorResponse(
            description="Слишком много запросов",
            code="TOO_MANY_REQUESTS",
            exceptionName=exc.__class__.__name__,
            exceptionMessage=str(exc),
            stacktrace=[],
        ).model_dump(exclude_none=True)

        return JSONResponse(status_code=429, content=body)

    return app
