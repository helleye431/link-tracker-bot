from scrapper_service.infrastructure.database.postgres.repositories.orm.orm_tracking_repository import (
    OrmTrackingRepository,
)
from scrapper_service.infrastructure.database.postgres.repositories.raw_sql.raw_sql_tracking_repository import (
    RawSqlTrackingRepository,
)
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)


async def build_repository(
    access_type: str,
    orm_url: str,
    raw_sql_url: str,
) -> TrackingRepositoryPort:

    match access_type:
        case "sql":
            return await RawSqlTrackingRepository.create(raw_sql_url)
        case "orm":
            return OrmTrackingRepository(orm_url)
        case _:
            raise ValueError(f"Неизвестный тип доступа: {access_type}")
