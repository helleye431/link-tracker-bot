from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    ARRAY,
    BOOLEAN,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ChatOrm(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    subscriptions: Mapped[list["LinkChatOrm"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )


class LinkOrm(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    last_seen_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subscriptions: Mapped[list["LinkChatOrm"]] = relationship(
        back_populates="link",
        cascade="all, delete-orphan",
    )


class LinkChatOrm(Base):
    __tablename__ = "link_chat"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True,
    )
    link_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("links.id", ondelete="CASCADE"),
        primary_key=True,
    )

    chat: Mapped["ChatOrm"] = relationship(back_populates="subscriptions")
    link: Mapped["LinkOrm"] = relationship(back_populates="subscriptions")

    tags: Mapped[list["LinkTagOrm"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )
    filters: Mapped[list["LinkFilterOrm"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class LinkTagOrm(Base):
    __tablename__ = "link_tags"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tag_name: Mapped[str] = mapped_column(Text, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "link_id"],
            ["link_chat.chat_id", "link_chat.link_id"],
            ondelete="CASCADE",
        ),
    )

    subscription: Mapped["LinkChatOrm"] = relationship(back_populates="tags")


class LinkFilterOrm(Base):
    __tablename__ = "link_filters"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    link_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    filter_name: Mapped[str] = mapped_column(Text, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "link_id"],
            ["link_chat.chat_id", "link_chat.link_id"],
            ondelete="CASCADE",
        ),
    )

    subscription: Mapped["LinkChatOrm"] = relationship(back_populates="filters")


class UpdateEventsOutboxOrm(Base):
    __tablename__ = "update_events_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    update_id: Mapped[int] = mapped_column(BigInteger)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    tg_chat_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)
    is_error: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
