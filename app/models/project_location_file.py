import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectLocationFile(Base):
    __tablename__ = "project_location_files"

    project_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_locations.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
