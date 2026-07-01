from fastapi import APIRouter, Depends, Path, Request, Response

from scrapper_service.application.exceptions.chat_exceptions import (
    ChatAlreadyExistsError,
    ChatNotFoundError,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.presentation.http.schemas.responses import ApiErrorResponse
from scrapper_service.presentation.http.utils.error_response import error_response


router = APIRouter(prefix="/tg-chat", tags=["tg-chat"])


def get_tracking_service(request: Request) -> TrackingService:
    return request.app.state.tracking_service


@router.post(
    "/{id}",
    status_code=200,
    summary="Зарегистрировать чат",
    response_class=Response,
    responses={
        200: {"description": "Чат зарегистрирован", "content": {}},
        400: {
            "description": "Некорректные параметры запроса",
            "model": ApiErrorResponse,
        },
        409: {"description": "Чат уже существует", "model": ApiErrorResponse},
    },
)
async def register_chat(
    id: int = Path(..., description="Telegram chat id"),
    service: TrackingService = Depends(get_tracking_service),
):
    chat_id = id

    try:
        await service.register_chat(chat_id)
        return Response(status_code=200)
    except ChatAlreadyExistsError as exc:
        return error_response(
            409,
            "Чат уже существует",
            "CHAT_ALREADY_EXISTS",
            exc,
        )


@router.delete(
    "/{id}",
    status_code=200,
    summary="Удалить чат",
    response_class=Response,
    responses={
        200: {"description": "Чат успешно удалён", "model": {}},
        400: {
            "description": "Некорректные параметры запроса",
            "model": ApiErrorResponse,
        },
        404: {
            "description": "Чат не существует",
            "model": ApiErrorResponse,
        },
    },
)
async def delete_chat(
    id: int = Path(..., description="Telegram chat id"),
    service: TrackingService = Depends(get_tracking_service),
):
    chat_id = id

    try:
        await service.delete_chat(chat_id)
        return Response(status_code=200)
    except ChatNotFoundError as exc:
        return error_response(
            404,
            "Чат не существует",
            "CHAT_NOT_FOUND",
            exc,
        )
