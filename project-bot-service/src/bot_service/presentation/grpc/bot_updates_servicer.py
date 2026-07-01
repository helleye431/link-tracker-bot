from pydantic import ValidationError
import structlog

from bot_service.application.services.update_service import UpdateService
from bot_service.presentation.grpc.contracts.own import bot_pb2, bot_pb2_grpc


logger = structlog.get_logger(__name__)


def build_error(
    description: str,
    code: str,
    exc: Exception | None = None,
) -> bot_pb2.ApiErrorResponse:
    return bot_pb2.ApiErrorResponse(
        description=description,
        code=code,
        exceptionName=exc.__class__.__name__ if exc else "",
        exceptionMessage=str(exc) if exc else "",
        stacktrace=[],
    )


class BotUpdatesServicer(bot_pb2_grpc.BotUpdatesServiceServicer):
    """
    gRPC-входная точка bot-сервиса для приёма обновлений от внешних сервисов.

    Принимает запрос на рассылку обновления и делегирует выполнение
    в UpdateService.
    """

    def __init__(self, update_service: UpdateService):
        self.update_service = update_service

    async def SendUpdate(self, request, context):
        logger.info(
            "send_update_called",
            method="SendUpdate",
            url=request.url,
            tg_chat_ids=list(request.tgChatIds),
            tg_chat_ids_count=len(request.tgChatIds),
        )

        try:
            await self.update_service.send_updates(
                url=request.url,
                tg_chat_ids=list(request.tgChatIds),
                description=request.description,
            )

            logger.info(
                "send_update_succeeded",
                method="SendUpdate",
                url=request.url,
                tg_chat_ids_count=len(request.tgChatIds),
            )
            return bot_pb2.SendUpdateResult(
                data=bot_pb2.EmptyData(),
            )

        except ValidationError as exc:
            logger.warning(
                "send_update_failed_validation_error",
                method="SendUpdate",
                url=request.url,
                error=str(exc),
            )
            return bot_pb2.SendUpdateResult(
                error=build_error(
                    "Некорректные параметры запроса",
                    "BAD_REQUEST",
                    exc,
                )
            )

        except ValueError as exc:
            logger.warning(
                "send_update_failed_bad_request",
                method="SendUpdate",
                url=request.url,
                error=str(exc),
            )
            return bot_pb2.SendUpdateResult(
                error=build_error(
                    "Некорректные параметры запроса",
                    "BAD_REQUEST",
                    exc,
                )
            )

        except Exception as exc:
            logger.exception(
                "send_update_failed_unexpected",
                method="SendUpdate",
                url=request.url,
                error=str(exc),
            )
            return bot_pb2.SendUpdateResult(
                error=build_error(
                    "Внутренняя ошибка сервиса",
                    "INTERNAL_ERROR",
                    exc,
                )
            )
