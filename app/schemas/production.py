import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import (
    LocationType,
    ProductionLocationStatus,
    ProductionRole,
    ProductionStatus,
)
from app.schemas.file import FeaturedImageResponse


class ProductionCreate(BaseModel):
    name: str
    description: str | None = None


class ProductionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProductionStatus | None = None


class ProductionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    status: ProductionStatus
    my_role: ProductionRole
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductionMemberCreate(BaseModel):
    email: EmailStr
    role: ProductionRole = ProductionRole.MEMBER


class ProductionMemberUpdate(BaseModel):
    role: ProductionRole


class ProductionMemberResponse(BaseModel):
    production_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    email: str
    role: ProductionRole
    joined_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductionLocationCreate(BaseModel):
    location_id: uuid.UUID
    notes: str | None = None


class ProductionLocationUpdate(BaseModel):
    status: ProductionLocationStatus | None = None
    notes: str | None = None


class ProductionLocationAddedBy(BaseModel):
    id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class ProductionLocationLocationSummary(BaseModel):
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


class ProductionLocationResponse(BaseModel):
    production_id: uuid.UUID
    location_id: uuid.UUID
    added_by_id: uuid.UUID
    status: ProductionLocationStatus
    notes: str | None = None
    added_by: ProductionLocationAddedBy
    location: ProductionLocationLocationSummary
    added_at: datetime | None = None

    model_config = {"from_attributes": True}
