from sqlalchemy import create_engine, text


def test_migrations_applied(migration_sync_url: str):
    engine = create_engine(migration_sync_url)

    try:
        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text(
                        """
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname = 'public'
                        """
                    )
                )
            }

        assert "chats" in tables
        assert "links" in tables
        assert "link_chat" in tables
        assert "link_tags" in tables
        assert "link_filters" in tables
        assert "alembic_version" in tables
    finally:
        engine.dispose()
