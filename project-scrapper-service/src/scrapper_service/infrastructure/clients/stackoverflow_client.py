from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from scrapper_service.application.exceptions.external_client_exceptions import (
    StackoverflowLinkValidationError,
    StackoverflowServiceError,
)
from scrapper_service.application.ports.external_client_port import ExternalClientPort
from scrapper_service.domain.models.link_update_event import LinkUpdateEvent
import structlog
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)
from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_request_duration,
)

logger = structlog.get_logger(__name__)


class StackoverflowClient(ExternalClientPort):
    def __init__(self, base_url: str, client: ResilientHttpClient | None = None):
        self.base_url = base_url.rstrip("/")
        if client is None:
            self.client = httpx.AsyncClient(timeout=10)
        else:
            self.client = client

    @property
    def domain(self) -> str:
        return "stackoverflow.com"

    @staticmethod
    def parse_url(url: str) -> int:
        try:
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            question_id = int(parts[1])
        except (IndexError, ValueError, TypeError):
            raise StackoverflowLinkValidationError

        return question_id

    @observe_request_duration(scope="external_source", scope_type="stackoverflow")
    async def get_latest_event(self, url: str) -> LinkUpdateEvent | None:
        question_id = self.parse_url(url)

        answers_url = f"{self.base_url}/questions/{question_id}/answers"
        comments_url = f"{self.base_url}/questions/{question_id}/comments"
        question_url = f"{self.base_url}/questions/{question_id}"

        params = {"site": "stackoverflow", "sort": "creation", "order": "desc"}

        try:
            question_resp = await self.client.get(question_url, params=params)
            question_resp.raise_for_status()
            question_items = question_resp.json()["items"]
            if not question_items:
                return None

            question_title = question_items[0]["title"]

            answers_resp = await self.client.get(
                answers_url,
                params={**params, "filter": "withbody"},
            )
            answers_resp.raise_for_status()
            answers = answers_resp.json().get("items", [])

            comments_resp = await self.client.get(comments_url, params=params)
            comments_resp.raise_for_status()
            comments = comments_resp.json().get("items", [])

            candidates = []

            for answer in answers[:1]:
                candidates.append(
                    LinkUpdateEvent(
                        url=url,
                        event_type="stackoverflow_answer",
                        title=question_title,
                        author=answer.get("owner", {}).get("display_name", "unknown"),
                        created_at=datetime.fromtimestamp(
                            answer["creation_date"], tz=timezone.utc
                        ),
                        preview=answer.get("body"),
                    )
                )

            for comment in comments[:1]:
                candidates.append(
                    LinkUpdateEvent(
                        url=url,
                        event_type="stackoverflow_comment",
                        title=question_title,
                        author=comment.get("owner", {}).get("display_name", "unknown"),
                        created_at=datetime.fromtimestamp(
                            comment["creation_date"], tz=timezone.utc
                        ),
                        preview=comment.get("body"),
                    )
                )

            if not candidates:
                return None

            return max(candidates, key=lambda item: item.created_at)

        except httpx.TimeoutException:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise StackoverflowServiceError

    @observe_request_duration(scope="external_source", scope_type="stackoverflow")
    async def get_last_update(self, url: str) -> datetime | None:
        question_id = self.parse_url(url)
        api_url = f"{self.base_url}/questions/{question_id}"
        params: dict[str, str] = {"site": "stackoverflow"}

        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()["items"][0]
            return datetime.fromtimestamp(data["last_activity_date"], tz=timezone.utc)
        except httpx.TimeoutException:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise StackoverflowServiceError

    async def aclose(self) -> None:
        await self.client.aclose()
        logger.info("stackoverflow_client_closed")
