import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class File(Base):
    __tablename__ = "files"
    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "polymorphic_on": "type",
        "polymorphic_identity": "file",
    }

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(20))

    # Ownership
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    # Upload lifecycle
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Metadata
    file_category: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    # User-editable
    caption: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Image-specific (nullable, only populated for Image rows)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    thumbnail_key: Mapped[str | None] = mapped_column(String(500))


class Image(File):
    __mapper_args__: dict[str, Any] = {"polymorphic_identity": "image"}  # noqa: RUF012
