import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.enums import (
    ProductionLocationStatus,
    ProductionRole,
    ProductionStatus,
)


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
    status: str
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
    role: str
    joined_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductionLocationCreate(BaseModel):
    location_id: uuid.UUID
    notes: str | None = None


class ProductionLocationUpdate(BaseModel):
    status: ProductionLocationStatus | None = None
    notes: str | None = None


class ProductionLocationResponse(BaseModel):
    production_id: uuid.UUID
    location_id: uuid.UUID
    added_by_id: uuid.UUID
    status: str
    notes: str | None = None
    added_at: datetime | None = None

    model_config = {"from_attributes": True}
