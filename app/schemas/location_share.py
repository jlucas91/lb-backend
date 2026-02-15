import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SharePermission


class LocationShareCreate(BaseModel):
    shared_with_id: uuid.UUID
    permission: SharePermission = SharePermission.VIEW


class LocationShareResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    shared_by_id: uuid.UUID
    shared_with_id: uuid.UUID
    permission: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
