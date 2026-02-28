"""SmugMug sync helpers.

Reusable async functions called by Celery tasks in app.tasks.smugmug.
Each function takes a db session and operates on specific models.
"""

import logging
import mimetypes
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.storage import S3StorageService
from app.models.enums import FileType
from app.models.file import Image
from app.models.smugmug import (
    SmugmugAccount,
    SmugmugFolder,
    SmugmugGallery,
    SmugmugImage,
)
from app.services.smugmug_client import extract_filename, pick_best_image_url

logger = logging.getLogger(__name__)

# SmugMug node types
_NODE_TYPE_FOLDER = 2
_NODE_TYPE_ALBUM = 4


@asynccontextmanager
async def task_session() -> AsyncGenerator[AsyncSession]:
    """Create a standalone async session for use in Celery tasks.

    Each task gets its own engine with a long command_timeout suitable
    for sync operations (image downloads, large upserts).
    """
    engine = create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 10, "command_timeout": 300},
    )
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


async def upsert_nodes(
    db: AsyncSession,
    account: SmugmugAccount,
    nodes: list[dict[str, Any]],
) -> tuple[dict[str, uuid.UUID], list[tuple[uuid.UUID, str, str]]]:
    """Partition nodes into folders and galleries, upsert both.

    Returns:
        folder_uri_to_id: mapping of SmugMug NodeID -> our folder UUID
        gallery_data: list of (gallery_uuid, album_id_str, album_key)
                      for image fetching
    """
    now = datetime.now(UTC)

    # Identify the root ParentID (the invisible root node).
    # All depth=1 nodes share the same ParentID.
    root_parent_id: str | None = None
    for node in nodes:
        if node.get("Depth") == 1:
            root_parent_id = str(node.get("ParentID", ""))
            break

    # Partition nodes by type
    folder_nodes = [n for n in nodes if n.get("Type") == _NODE_TYPE_FOLDER]
    album_nodes = [n for n in nodes if n.get("Type") == _NODE_TYPE_ALBUM]

    # --- Upsert folders (process first so gallery parent lookups work) ---
    existing_folders_result = await db.execute(
        select(SmugmugFolder).where(SmugmugFolder.account_id == account.id)
    )
    existing_folders = {
        f.smugmug_uri: f for f in existing_folders_result.scalars().all()
    }

    # First pass: create/update folders without parent_id
    folder_uri_to_id: dict[str, uuid.UUID] = {}
    for idx, node in enumerate(folder_nodes):
        node_id = str(node["NodeID"])
        folder = existing_folders.get(node_id)
        if folder is None:
            folder = SmugmugFolder(
                account_id=account.id,
                smugmug_uri=node_id,
            )
            db.add(folder)
        folder.name = str(node.get("Name", ""))
        folder.url_path = str(node.get("UrlPath", "")) or None
        folder.sort_order = idx
        folder.last_synced_at = now
        folder_uri_to_id[node_id] = folder.id

    await db.flush()

    # Second pass: set parent_id now that all folders exist
    for node in folder_nodes:
        node_id = str(node["NodeID"])
        parent_node_id = str(node.get("ParentID", ""))
        folder = existing_folders.get(node_id)
        if folder is None:
            folder_result = await db.execute(
                select(SmugmugFolder).where(
                    SmugmugFolder.account_id == account.id,
                    SmugmugFolder.smugmug_uri == node_id,
                )
            )
            folder = folder_result.scalar_one_or_none()
        if folder is None:
            continue

        if parent_node_id and parent_node_id != root_parent_id:
            folder.parent_id = folder_uri_to_id.get(parent_node_id)
        else:
            folder.parent_id = None

    await db.flush()

    # --- Upsert galleries ---
    existing_galleries_result = await db.execute(
        select(SmugmugGallery).where(SmugmugGallery.account_id == account.id)
    )
    existing_galleries = {
        g.smugmug_uri: g for g in existing_galleries_result.scalars().all()
    }

    gallery_data: list[tuple[uuid.UUID, str, str]] = []
    for idx, node in enumerate(album_nodes):
        node_id = str(node["NodeID"])
        parent_node_id = str(node.get("ParentID", ""))
        remote_id = str(node.get("RemoteID", ""))
        remote_key = str(node.get("RemoteKey", ""))

        gallery = existing_galleries.get(node_id)
        if gallery is None:
            gallery = SmugmugGallery(
                account_id=account.id,
                smugmug_uri=node_id,
            )
            db.add(gallery)

        gallery.name = str(node.get("Name", ""))
        gallery.description = str(node.get("Description", "")) or None
        gallery.url_path = str(node.get("UrlPath", "")) or None
        gallery.smugmug_album_key = remote_key or None
        gallery.sort_order = idx
        gallery.last_synced_at = now

        # Link to parent folder
        if parent_node_id and parent_node_id != root_parent_id:
            gallery.folder_id = folder_uri_to_id.get(parent_node_id)
        else:
            gallery.folder_id = None

        gallery_data.append((gallery.id, remote_id, remote_key))

    await db.flush()

    logger.info(
        "Upserted %d folders, %d galleries for account %s",
        len(folder_nodes),
        len(album_nodes),
        account.id,
    )
    return folder_uri_to_id, gallery_data


async def upsert_images(
    db: AsyncSession,
    gallery_id: uuid.UUID,
    images: list[dict[str, Any]],
) -> list[SmugmugImage]:
    """Upsert image metadata for a single gallery.

    Returns all upserted SmugmugImage records (caller can check file_id
    to decide which need downloading).
    """
    now = datetime.now(UTC)

    existing_result = await db.execute(
        select(SmugmugImage).where(SmugmugImage.gallery_id == gallery_id)
    )
    existing = {img.smugmug_uri: img for img in existing_result.scalars().all()}

    upserted: list[SmugmugImage] = []
    for image_data in images:
        image_key = str(image_data.get("ImageKey", ""))
        if not image_key:
            continue

        image = existing.get(image_key)
        if image is None:
            image = SmugmugImage(
                gallery_id=gallery_id,
                smugmug_uri=image_key,
            )
            db.add(image)

        image.smugmug_image_key = image_key
        image.filename = extract_filename(image_data)
        image.caption = str(image_data.get("Caption", "")) or None
        image.width = (
            int(image_data["OriginalWidth"])
            if image_data.get("OriginalWidth")
            else None
        )
        image.height = (
            int(image_data["OriginalHeight"])
            if image_data.get("OriginalHeight")
            else None
        )

        sizes = image_data.get("Sizes")
        if isinstance(sizes, dict):
            image.smugmug_url = pick_best_image_url(sizes)

        image.last_synced_at = now
        upserted.append(image)

    await db.flush()
    return upserted


async def update_gallery_image_count(
    db: AsyncSession,
    gallery_id: uuid.UUID,
    total_count: int,
) -> None:
    """Update the image_count on a gallery."""
    result = await db.execute(
        select(SmugmugGallery).where(SmugmugGallery.id == gallery_id)
    )
    gallery = result.scalar_one_or_none()
    if gallery is not None:
        gallery.image_count = total_count
        await db.flush()


async def download_and_store_image(
    db: AsyncSession,
    image_id: uuid.UUID,
    user_id: uuid.UUID,
    storage: S3StorageService,
) -> None:
    """Download a SmugMug image and store it in S3.

    Loads the SmugmugImage by ID, downloads from its smugmug_url,
    uploads to S3, and links the resulting File record.
    """
    result = await db.execute(select(SmugmugImage).where(SmugmugImage.id == image_id))
    image = result.scalar_one_or_none()
    if image is None or not image.smugmug_url or image.file_id is not None:
        return

    async with httpx.AsyncClient() as http:
        resp = await http.get(image.smugmug_url, follow_redirects=True)
        resp.raise_for_status()
        data = resp.content

    content_type = mimetypes.guess_type(image.filename)[0] or "image/jpeg"
    storage_key = f"smugmug/{uuid.uuid4()}/{image.filename}"
    size_bytes = await storage.upload_object(storage_key, data, content_type)

    file_record = Image(
        uploaded_by_id=user_id,
        status="active",
        file_category=FileType.PHOTO.value,
        storage_key=storage_key,
        filename=image.filename,
        content_type=content_type,
        size_bytes=size_bytes,
        width=image.width,
        height=image.height,
    )
    db.add(file_record)
    await db.flush()

    image.file_id = file_record.id
    await db.flush()
