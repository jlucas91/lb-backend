import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LocationShare(Base):
    __tablename__ = "location_shares"
    __table_args__ = (UniqueConstraint("location_id", "shared_with_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), index=True
    )
    shared_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    shared_with_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    permission: Mapped[str] = mapped_column(String(10), default="view")
    created_at: Mapped[datetime | None] = mapped_column(server_default=func.now())
