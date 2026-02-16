import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import LocationType
from app.schemas.file import FeaturedImageResponse


class ProjectLocationCreate(BaseModel):
    address: str
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None


class ProjectLocationCopy(BaseModel):
    location_id: uuid.UUID


class ProjectLocationUpdate(BaseModel):
    address: str | None = None
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None
    featured_file_id: uuid.UUID | None = None


class ProjectLocationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    added_by_id: uuid.UUID
    address: str
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None
    featured_image: FeaturedImageResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectLocationListResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    added_by_id: uuid.UUID
    address: str
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    location_type: LocationType | None = None
    featured_image: FeaturedImageResponse | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
