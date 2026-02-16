from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.location import LocationFieldsMixin

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.location import UserLocation


class ProjectLocation(LocationFieldsMixin, Base):
    __tablename__ = "project_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    added_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    source_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_locations.id", ondelete="SET NULL")
    )
    featured_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    source_location: Mapped[UserLocation | None] = relationship(lazy="raise")
    featured_file: Mapped[File | None] = relationship(lazy="noload")
