"""empty message

Revision ID: 2c482f8871fc
Revises: 
Create Date: 2026-04-05 14:09:59.969867

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2c482f8871fc"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id BIGINT PRIMARY KEY
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id BIGSERIAL PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            last_seen_update TIMESTAMPTZ NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS link_chat (
            chat_id BIGINT NOT NULL,
            link_id BIGINT NOT NULL,
            PRIMARY KEY (chat_id, link_id),
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
            FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS link_tags (
            chat_id BIGINT NOT NULL,
            link_id BIGINT NOT NULL,
            tag_name TEXT NOT NULL,
            PRIMARY KEY (chat_id, link_id, tag_name),
            FOREIGN KEY (chat_id, link_id)
                REFERENCES link_chat(chat_id, link_id)
                ON DELETE CASCADE
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS link_filters (
            chat_id BIGINT NOT NULL,
            link_id BIGINT NOT NULL,
            filter_name TEXT NOT NULL,
            PRIMARY KEY (chat_id, link_id, filter_name),
            FOREIGN KEY (chat_id, link_id)
                REFERENCES link_chat(chat_id, link_id)
                ON DELETE CASCADE
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS link_filters;")
    op.execute("DROP TABLE IF EXISTS link_tags;")
    op.execute("DROP TABLE IF EXISTS link_chat;")
    op.execute("DROP TABLE IF EXISTS links;")
    op.execute("DROP TABLE IF EXISTS chats;")
