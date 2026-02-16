import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.file import FeaturedImageResponse


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
    featured_file_id: uuid.UUID | None = None


class ScriptedLocationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    episode_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    sort_order: int
    featured_image: FeaturedImageResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScriptedLocationLocationCreate(BaseModel):
    project_location_id: uuid.UUID
    notes: str | None = None


class UserSummary(BaseModel):
    id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class ProjectLocationSummary(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str | None = None
    address: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class ScriptedLocationLocationResponse(BaseModel):
    project_location_id: uuid.UUID
    added_by: UserSummary
    notes: str | None = None
    added_at: datetime | None = None
    location: ProjectLocationSummary

    model_config = {"from_attributes": True}
