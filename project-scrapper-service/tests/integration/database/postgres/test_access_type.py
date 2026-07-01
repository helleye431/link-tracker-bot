import pytest
from scrapper_service.setup.config.settings import Settings
from scrapper_service.setup.ioc.repository_builder import (
    build_repository,
)
from scrapper_service.infrastructure.database.postgres.repositories.orm.orm_tracking_repository import (
    OrmTrackingRepository,
)
from scrapper_service.infrastructure.database.postgres.repositories.raw_sql.raw_sql_tracking_repository import (
    RawSqlTrackingRepository,
)


@pytest.mark.asyncio
async def test_access_type_raw_sql(monkeypatch):
    monkeypatch.setenv("access_type", "sql")
    settings = Settings()

    tracking_repo = await build_repository(
        access_type=settings.access_type,
        orm_url=settings.database_url_asyncpg,
        raw_sql_url=settings.database_url_asyncpg_driver,
    )

    assert isinstance(tracking_repo, RawSqlTrackingRepository)
    await tracking_repo.aclose()


@pytest.mark.asyncio
async def test_access_type_orm(monkeypatch):
    monkeypatch.setenv("access_type", "orm")
    settings = Settings()

    tracking_repo = await build_repository(
        access_type=settings.access_type,
        orm_url=settings.database_url_asyncpg,
        raw_sql_url=settings.database_url_asyncpg_driver,
    )

    assert isinstance(tracking_repo, OrmTrackingRepository)
    await tracking_repo.aclose()


@pytest.mark.asyncio
async def test_access_type_error(monkeypatch):
    monkeypatch.setenv("access_type", "sql-orm")
    settings = Settings()

    with pytest.raises(ValueError, match="Неизвестный тип доступа: sql-orm"):
        await build_repository(
            access_type=settings.access_type,
            orm_url=settings.database_url_asyncpg,
            raw_sql_url=settings.database_url_asyncpg_driver,
        )
