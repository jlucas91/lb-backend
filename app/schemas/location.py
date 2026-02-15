import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import LocationType


class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: LocationType | None = None
    description: str | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_type: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    location_type: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
