import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ScoutingStatus


class ScoutingCreate(BaseModel):
    scouted_at: datetime
    notes: str | None = None
    status: ScoutingStatus = ScoutingStatus.DRAFT


class ScoutingUpdate(BaseModel):
    scouted_at: datetime | None = None
    notes: str | None = None
    status: ScoutingStatus | None = None


class ScoutingResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    scouted_by_id: uuid.UUID
    notes: str | None = None
    scouted_at: datetime
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScoutingListResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    scouted_by_id: uuid.UUID
    scouted_at: datetime
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
