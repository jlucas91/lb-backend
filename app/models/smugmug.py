import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmugmugAccount(Base):
    __tablename__ = "smugmug_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    smugmug_nick: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(255))
    sync_status: Mapped[str] = mapped_column(String(20), default="idle")
    last_synced_at: Mapped[datetime | None] = mapped_column()
    sync_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class SmugmugFolder(Base):
    __tablename__ = "smugmug_folders"
    __table_args__ = (
        UniqueConstraint("account_id", "smugmug_uri", name="uq_smugmug_folder_uri"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("smugmug_accounts.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("smugmug_folders.id", ondelete="SET NULL")
    )
    smugmug_uri: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(500))
    url_path: Mapped[str | None] = mapped_column(String(1000))
    sort_order: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class SmugmugGallery(Base):
    __tablename__ = "smugmug_galleries"
    __table_args__ = (
        UniqueConstraint("account_id", "smugmug_uri", name="uq_smugmug_gallery_uri"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("smugmug_accounts.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("smugmug_folders.id", ondelete="SET NULL")
    )
    smugmug_uri: Mapped[str] = mapped_column(String(500))
    smugmug_album_key: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    url_path: Mapped[str | None] = mapped_column(String(1000))
    sort_order: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class SmugmugImage(Base):
    __tablename__ = "smugmug_images"
    __table_args__ = (
        UniqueConstraint("gallery_id", "smugmug_uri", name="uq_smugmug_image_uri"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    gallery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("smugmug_galleries.id", ondelete="CASCADE"), index=True
    )
    smugmug_uri: Mapped[str] = mapped_column(String(500))
    smugmug_image_key: Mapped[str | None] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    smugmug_url: Mapped[str | None] = mapped_column(String(1000))
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL")
    )
    last_synced_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
