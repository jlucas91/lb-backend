from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project_location import ProjectLocation
    from app.models.user import User


class ScriptedLocationLocation(Base):
    __tablename__ = "scripted_location_locations"

    scripted_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scripted_locations.id", ondelete="CASCADE"), primary_key=True
    )
    project_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_locations.id", ondelete="CASCADE"), primary_key=True
    )
    added_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime | None] = mapped_column(server_default=func.now())

    project_location: Mapped[ProjectLocation] = relationship(lazy="raise")
    added_by: Mapped[User] = relationship(lazy="raise")
