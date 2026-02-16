import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.location import LocationFieldsMixin


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
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
