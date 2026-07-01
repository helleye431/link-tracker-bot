import grpc
import structlog

from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.presentation.grpc.contracts.external import bot_pb2, bot_pb2_grpc

logger = structlog.get_logger(__name__)


class GrpcBotClient(NotificationClientPort):
    def __init__(self, target: str):
        self.target = target
        self.channel = grpc.aio.insecure_channel(target)
        self.stub = bot_pb2_grpc.BotUpdatesServiceStub(self.channel)

    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        chat_ids: list[int],
        is_error: bool,
    ) -> None:
        request = bot_pb2.LinkUpdateRequest(
            id=update_id,
            url=url,
            description=description,
            tgChatIds=chat_ids,
        )

        logger.info(
            "bot_client_send_update_started",
            update_id=update_id,
            url=url,
            chats_count=len(chat_ids),
        )

        try:
            response = await self.stub.SendUpdate(request)

            if response.HasField("error"):
                logger.warning(
                    "client error",
                    code=response.error.code,
                    description=response.error.description,
                    chats_count=len(chat_ids),
                )
                return

        except Exception as exc:
            logger.warning(
                "client error",
                exception=str(exc),
                chats_count=len(chat_ids),
            )
        else:
            logger.info(
                "bot_client_send_update_succeeded",
                update_id=update_id,
                url=url,
                chats_count=len(chat_ids),
            )

    async def aclose(self) -> None:
        await self.channel.close()
        logger.info("bot_client_closed", transport="grpc")
