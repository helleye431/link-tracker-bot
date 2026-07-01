from fastapi import APIRouter, Depends, Request
from bot_service.presentation.http.schemas.requests import LinkUpdate
from bot_service.application.services.update_service import UpdateService
from bot_service.presentation.http.schemas.responses import ApiErrorResponse

update_router = APIRouter()


def get_update_service(request: Request) -> UpdateService:
    return request.app.state.update_service


@update_router.post(
    "/updates",
    status_code=200,
    summary="Отправить обновление",
    response_model=None,
    response_description="Обновление обработано",
    responses={
        400: {
            "description": "Некорректные параметры запроса",
            "model": ApiErrorResponse,
        }
    },
)
async def send_updates(
    update: LinkUpdate, update_service: UpdateService = Depends(get_update_service)
) -> None:
    if update.is_error:
        await update_service.send_error_report(
            url=update.url, tg_chat_ids=update.tgChatIds, description=update.description
        )
    else:
        await update_service.send_updates(
            url=update.url, tg_chat_ids=update.tgChatIds, description=update.description
        )
