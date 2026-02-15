import uuid
from datetime import datetime

from pydantic import BaseModel


class PresignRequest(BaseModel):
    filename: str
    content_type: str


class PresignResponse(BaseModel):
    upload_url: str
    storage_key: str


class FileConfirm(BaseModel):
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int | None = None
    caption: str | None = None


class FileUpdate(BaseModel):
    caption: str | None = None
    sort_order: int | None = None


class FileResponse(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    file_type: str
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int | None = None
    caption: str | None = None
    sort_order: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
