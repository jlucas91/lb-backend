import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScriptedLocationLocation(Base):
    __tablename__ = "scripted_location_locations"

    scripted_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scripted_locations.id", ondelete="CASCADE"), primary_key=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id"), primary_key=True
    )
    added_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
