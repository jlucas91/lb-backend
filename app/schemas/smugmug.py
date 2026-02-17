import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SmugmugSyncStatus

# --- Account schemas ---


class SmugmugAccountCreate(BaseModel):
    username: str
    password: str
    nickname: str | None = None


class SmugmugAccountUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    nickname: str | None = None


class SmugmugAccountResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    nickname: str | None = None
    sync_status: SmugmugSyncStatus
    last_synced_at: datetime | None = None
    sync_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Folder schemas ---


class SmugmugFolderResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    smugmug_uri: str
    name: str
    url_path: str | None = None
    sort_order: int | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Gallery schemas ---


class SmugmugGalleryResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    folder_id: uuid.UUID | None = None
    smugmug_uri: str
    smugmug_album_key: str | None = None
    name: str
    description: str | None = None
    image_count: int
    url_path: str | None = None
    sort_order: int | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Image schemas ---


class SmugmugImageResponse(BaseModel):
    id: uuid.UUID
    gallery_id: uuid.UUID
    smugmug_uri: str
    smugmug_image_key: str | None = None
    filename: str
    caption: str | None = None
    width: int | None = None
    height: int | None = None
    smugmug_url: str | None = None
    file_id: uuid.UUID | None = None
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Gallery detail (with images) ---


class SmugmugGalleryDetailResponse(SmugmugGalleryResponse):
    images: list[SmugmugImageResponse] = []


# --- Folder tree (recursive) ---


class SmugmugFolderTree(BaseModel):
    id: uuid.UUID
    name: str
    smugmug_uri: str
    url_path: str | None = None
    sort_order: int | None = None
    children: list["SmugmugFolderTree"] = []
    galleries: list[SmugmugGalleryResponse] = []

    model_config = {"from_attributes": True}
