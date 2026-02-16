import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import LocationType, SharePermission


class LocationShareCreate(BaseModel):
    shared_with_id: uuid.UUID
    permission: SharePermission = SharePermission.VIEW


class LocationShareResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    shared_by_id: uuid.UUID
    shared_with_id: uuid.UUID
    permission: SharePermission
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SharedWithUser(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str

    model_config = {"from_attributes": True}


class LocationShareListResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    shared_by_id: uuid.UUID
    shared_with_id: uuid.UUID
    permission: SharePermission
    created_at: datetime | None = None
    shared_with: SharedWithUser

    model_config = {"from_attributes": True}


class SharedFeaturedImage(BaseModel):
    id: uuid.UUID
    thumbnail_url: str | None = None
    download_url: str | None = None

    model_config = {"from_attributes": True}


class SharedLocationSummary(BaseModel):
    id: uuid.UUID
    name: str | None = None
    address: str
    city: str | None = None
    state: str | None = None
    country: str | None = None
    location_type: LocationType | None = None
    featured_image: SharedFeaturedImage | None = None

    model_config = {"from_attributes": True}


class SharedByUser(BaseModel):
    id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class SharedLocationDetailResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    shared_by_id: uuid.UUID
    shared_with_id: uuid.UUID
    permission: SharePermission
    created_at: datetime | None = None
    location: SharedLocationSummary
    shared_by: SharedByUser

    model_config = {"from_attributes": True}
