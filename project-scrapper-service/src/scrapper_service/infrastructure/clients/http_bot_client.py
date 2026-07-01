import httpx
import structlog

from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)
from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_request_duration,
)

logger = structlog.get_logger(__name__)


class HttpBotClient(NotificationClientPort):
    def __init__(self, base_url: str, client: ResilientHttpClient | None = None):
        self.base_url = base_url.rstrip("/")
        if client is None:
            self.client = httpx.AsyncClient(timeout=10)
        else:
            self.client = client

    @observe_request_duration(scope="external_source", scope_type="bot")
    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        chat_ids: list[int],
        is_error: bool,
    ):
        payload = {
            "id": update_id,
            "url": url,
            "description": description,
            "tgChatIds": chat_ids,
            "is_error": is_error,
            "priority": "MEDIUM",
        }

        logger.info(
            "bot_client_send_update_started",
            update_id=update_id,
            url=url,
            chats_count=len(chat_ids),
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/updates",
                json=payload,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise
        except Exception as exc:
            logger.warning(
                "http_bot_client_error", exception=str(exc), chats_count=len(chat_ids)
            )
            raise

        else:
            logger.info(
                "bot_client_send_update_succeeded",
                update_id=update_id,
                url=url,
                status_code=response.status_code,
            )

    async def aclose(self) -> None:
        await self.client.aclose()
        logger.info("bot_client_closed", transport="http")
