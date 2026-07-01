"""empty message

Revision ID: f60bb718d056
Revises: 97027e15db9b
Create Date: 2026-05-01 20:17:57.387375

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f60bb718d056"
down_revision: Union[str, Sequence[str], None] = "97027e15db9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE update_events_outbox (
            id BIGSERIAL PRIMARY KEY,
            update_id BIGINT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            description TEXT NOT NULL,
            author TEXT NOT NULL,
            tg_chat_ids BIGINT[] NOT NULL,
            is_error BOOLEAN NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            sent_at TIMESTAMPTZ
        );  

        CREATE INDEX idx_update_events_outbox_pending
            ON update_events_outbox (created_at)
            WHERE sent_at IS NULL;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TABLE IF EXISTS update_events_outbox
        """
    )
