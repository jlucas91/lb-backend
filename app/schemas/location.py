import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import LocationType
from app.schemas.file import FeaturedImageResponse


class UserLocationCreate(BaseModel):
    address: str
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None


class UserLocationUpdate(BaseModel):
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


class UserLocationResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
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


class UserLocationListResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    address: str
    name: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    location_type: LocationType | None = None
    featured_image: FeaturedImageResponse | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
