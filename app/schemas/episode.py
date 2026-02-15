import uuid
from datetime import datetime

from pydantic import BaseModel


class EpisodeCreate(BaseModel):
    name: str
    description: str | None = None
    sort_order: int = 0


class EpisodeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None


class EpisodeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None = None
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
