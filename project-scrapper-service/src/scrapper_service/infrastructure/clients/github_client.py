from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from scrapper_service.application.exceptions.external_client_exceptions import (
    GithubLinkValidationError,
    GithubServiceError,
)
from scrapper_service.application.ports.external_client_port import ExternalClientPort
from scrapper_service.domain.models.link_update_event import LinkUpdateEvent
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)
import structlog

from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_request_duration,
)

logger = structlog.get_logger(__name__)


class GithubClient(ExternalClientPort):
    def __init__(self, base_url: str, client: ResilientHttpClient | None = None):
        self.base_url = base_url.rstrip("/")
        if client is None:
            self.client = httpx.AsyncClient(timeout=10)
        else:
            self.client = client

    @property
    def domain(self) -> str:
        return "github.com"

    @staticmethod
    def parse_url(url: str) -> tuple[str, str]:
        try:
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            owner = parts[0]
            repo = parts[1]
        except (IndexError, ValueError, TypeError):
            raise GithubLinkValidationError
        return owner, repo

    @observe_request_duration(scope="external_source", scope_type="github")
    async def get_latest_event(self, url: str) -> LinkUpdateEvent | None:
        owner, repo = self.parse_url(url)

        api_url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params: dict[str, str | int] = {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "per_page": 1,
        }

        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            item = data[0]
            event_type = (
                "github_pull_request" if "pull_request" in item else "github_issue"
            )
            return LinkUpdateEvent(
                url=url,
                event_type=event_type,
                title=item["title"],
                author=item["user"]["login"],
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ).astimezone(timezone.utc),
                preview=item.get("body"),
            )
        except httpx.TimeoutException:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise GithubServiceError

    @observe_request_duration(scope="external_source", scope_type="github")
    async def get_last_update(self, url: str) -> datetime | None:
        owner, repo = self.parse_url(url)
        api_url = f"{self.base_url}/repos/{owner}/{repo}"

        try:
            response = await self.client.get(api_url)
            response.raise_for_status()
            data = response.json()
            return datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except httpx.TimeoutException:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise GithubServiceError

    async def aclose(self) -> None:
        await self.client.aclose()
        logger.info("github_client_closed")
