from fastapi import APIRouter, Depends, Header, Request
from scrapper_service.presentation.http.utils.error_response import error_response
from scrapper_service.application.exceptions.chat_exceptions import ChatNotFoundError
from scrapper_service.application.exceptions.link_exceptions import (
    LinkAlreadyExistsError,
    LinkNotFoundError,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.presentation.http.schemas.requests import (
    AddLinkRequest,
    RemoveLinkRequest,
)
from scrapper_service.presentation.http.schemas.responses import (
    ApiErrorResponse,
    LinkResponse,
    ListLinksResponse,
)

router = APIRouter(prefix="/links", tags=["links"])


def get_tracking_service(request: Request) -> TrackingService:
    return request.app.state.tracking_service


@router.get(
    "",
    response_model=ListLinksResponse,
    status_code=200,
    summary="Получить все отслеживаемые ссылки",
    response_description="Ссылки успешно получены",
    responses={
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
async def get_links(
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
    service: TrackingService = Depends(get_tracking_service),
):
    try:
        links = await service.get_links(tg_chat_id)

        return ListLinksResponse(
            links=[
                LinkResponse(
                    id=link.id,
                    url=link.url,
                    tags=link.tags,
                    filters=link.filters,
                    last_seen_update=link.last_seen_update,
                )
                for link in links
            ],
            size=len(links),
        )
    except ChatNotFoundError as exc:
        return error_response(
            404,
            "Чат не существует",
            "CHAT_NOT_FOUND",
            exc,
        )


@router.post(
    "",
    response_model=LinkResponse,
    status_code=200,
    summary="Добавить отслеживание ссылки",
    response_description="Ссылка успешно добавлена",
    responses={
        400: {
            "description": "Некорректные параметры запроса",
            "model": ApiErrorResponse,
        },
        404: {
            "description": "Чат не существует",
            "model": ApiErrorResponse,
        },
        409: {
            "description": "Ссылка уже отслеживается",
            "model": ApiErrorResponse,
        },
    },
)
async def add_link(
    body: AddLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
    service: TrackingService = Depends(get_tracking_service),
):
    try:
        created_link = await service.add_link(
            chat_id=tg_chat_id, url=str(body.link), tags=body.tags, filters=body.filters
        )

        return LinkResponse(
            id=created_link.id,
            url=created_link.url,
            tags=created_link.tags,
            filters=created_link.filters,
            last_seen_update=created_link.last_seen_update,
        )
    except ChatNotFoundError as exc:
        return error_response(
            404,
            "Чат не существует",
            "CHAT_NOT_FOUND",
            exc,
        )
    except LinkAlreadyExistsError as exc:
        return error_response(
            409,
            "Ссылка уже отслеживается",
            "LINK_ALREADY_EXISTS",
            exc,
        )


@router.delete(
    "",
    response_model=LinkResponse,
    status_code=200,
    summary="Убрать отслеживание ссылки",
    response_description="Ссылка успешно убрана",
    responses={
        400: {
            "description": "Некорректные параметры запроса",
            "model": ApiErrorResponse,
        },
        404: {
            "description": "Чат не существует или ссылка не найдена",
            "model": ApiErrorResponse,
        },
    },
)
async def delete_link(
    body: RemoveLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
    service: TrackingService = Depends(get_tracking_service),
):
    try:
        link = await service.remove_link(
            chat_id=tg_chat_id,
            url=str(body.link),
        )

        return LinkResponse(
            id=link.id,
            url=link.url,
            tags=link.tags,
            filters=link.filters,
            last_seen_update=link.last_seen_update,
        )
    except ChatNotFoundError as exc:
        return error_response(
            404,
            "Чат не существует или ссылка не найдена",
            "CHAT_NOT_FOUND",
            exc,
        )
    except LinkNotFoundError as exc:
        return error_response(
            404,
            "Ссылки не существует",
            "LINK_NOT_FOUND",
            exc,
        )
