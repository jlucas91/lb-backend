import uuid
from datetime import datetime

from pydantic import BaseModel


class ScriptedLocationCreate(BaseModel):
    name: str
    description: str | None = None
    episode_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    sort_order: int = 0


class ScriptedLocationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    episode_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    sort_order: int | None = None


class ScriptedLocationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScriptedLocationLocationCreate(BaseModel):
    location_id: uuid.UUID
    notes: str | None = None


class ScriptedLocationLocationResponse(BaseModel):
    scripted_location_id: uuid.UUID
    location_id: uuid.UUID
    added_by_id: uuid.UUID
    notes: str | None = None
    added_at: datetime | None = None

    model_config = {"from_attributes": True}
