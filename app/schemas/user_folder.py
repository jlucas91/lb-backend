import uuid
from datetime import datetime

from pydantic import BaseModel


class UserFolderCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class UserFolderUpdate(BaseModel):
    name: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None


class UserFolderResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
