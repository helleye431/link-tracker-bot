from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.infrastructure.database.valkey.utils.valkey_client import (
    ValkeyClient,
)
from scrapper_service.infrastructure.database.valkey.valkey_links_storage import (
    ValkeyLinksStorage,
)


async def build_tracking_service(
    tracking_repository: TrackingRepositoryPort,
    update_fetcher_service: LinkUpdateFetcherService,
    enable_cache: bool,
    valkey_enable_client_cache: bool,
    valkey_addresses: list[tuple[str, int]],
    valkey_cache_ttl: int,
    valkey_client_cache_ttl: int,
    valkey_client_cache_maxsize: int,
):
    if enable_cache:

        valkey_client = await ValkeyClient.create(
            valkey_addresses=valkey_addresses,
            enable_client_cache=valkey_enable_client_cache,
            client_cache_ttl=valkey_client_cache_ttl,
            client_cache_maxsize=valkey_client_cache_maxsize,
        )

        valkey_links_storage = ValkeyLinksStorage(
            client=valkey_client, ttl_seconds=valkey_cache_ttl
        )

        tracking_service = TrackingService(
            tracking_repository=tracking_repository,
            update_fetcher_service=update_fetcher_service,
            enable_cache=True,
            links_cache_storage=valkey_links_storage,
        )
    else:
        tracking_service = TrackingService(
            tracking_repository=tracking_repository,
            update_fetcher_service=update_fetcher_service,
            enable_cache=False,
        )

    return tracking_service
