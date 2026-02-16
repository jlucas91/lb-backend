import uuid
from datetime import datetime

from pydantic import BaseModel


# Upload flow
class UploadRequest(BaseModel):
    filename: str
    content_type: str


class UploadResponse(BaseModel):
    file_id: uuid.UUID
    upload_url: str
    storage_key: str


class ConfirmUpload(BaseModel):
    width: int | None = None
    height: int | None = None


# CRUD
class FileUpdate(BaseModel):
    caption: str | None = None
    sort_order: int | None = None


# Responses
class FileResponse(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    uploaded_by_id: uuid.UUID
    file_category: str
    storage_key: str
    filename: str
    content_type: str
    size_bytes: int | None = None
    caption: str | None = None
    sort_order: int
    download_url: str | None = None
    width: int | None = None
    height: int | None = None
    thumbnail_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# Entity attachment
class AttachFileRequest(BaseModel):
    file_id: uuid.UUID
