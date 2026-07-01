"""empty message

Revision ID: 97027e15db9b
Revises: 2c482f8871fc
Create Date: 2026-04-05 14:10:19.791041

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "97027e15db9b"
down_revision: Union[str, Sequence[str], None] = "2c482f8871fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_links_url
        ON links(url);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_link_chat_chat_id
        ON link_chat(chat_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_link_chat_link_id
        ON link_chat(link_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_link_tags_chat_link
        ON link_tags(chat_id, link_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_link_filters_chat_link
        ON link_filters(chat_id, link_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_link_filters_chat_link;")
    op.execute("DROP INDEX IF EXISTS idx_link_tags_chat_link;")
    op.execute("DROP INDEX IF EXISTS idx_link_chat_link_id;")
    op.execute("DROP INDEX IF EXISTS idx_link_chat_chat_id;")
    op.execute("DROP INDEX IF EXISTS idx_links_url;")
