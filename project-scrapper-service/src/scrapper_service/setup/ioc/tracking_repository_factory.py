from collections.abc import Awaitable, Callable

from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.setup.ioc.repository_builder import (
    build_repository,
)

TrackingRepositoryFactory = Callable[[], Awaitable[TrackingRepositoryPort]]


def make_tracking_repository_factory(
    access_type: str,
    orm_url: str,
    raw_sql_url: str,
) -> TrackingRepositoryFactory:

    async def factory() -> TrackingRepositoryPort:
        return await build_repository(
            access_type=access_type,
            orm_url=orm_url,
            raw_sql_url=raw_sql_url,
        )

    return factory
