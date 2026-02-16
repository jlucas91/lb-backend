import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScoutingFile(Base):
    __tablename__ = "scouting_files"

    scouting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scoutings.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
