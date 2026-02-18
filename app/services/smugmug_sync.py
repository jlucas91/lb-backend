"""SmugMug sync orchestrator.

Fetches folder/gallery/image data from SmugMug and upserts into the database.
See docs/smugmug-sync.md for full process documentation.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SmugmugSyncStatus
from app.models.smugmug import (
    SmugmugAccount,
    SmugmugFolder,
    SmugmugGallery,
    SmugmugImage,
)
from app.services.smugmug_client import (
    SmugmugClient,
    extract_filename,
    pick_best_image_url,
)

logger = logging.getLogger(__name__)

# SmugMug node types
_NODE_TYPE_FOLDER = 2
_NODE_TYPE_ALBUM = 4


async def sync_account(db: AsyncSession, account_id: uuid.UUID) -> None:
    """Run a full sync for a SmugMug account.

    This is the main entry point. It:
    1. Fetches the full node tree (folders + galleries)
    2. Upserts folders and galleries
    3. Fetches and upserts images for each gallery
    4. Updates sync status on completion or failure
    """
    result = await db.execute(
        select(SmugmugAccount).where(SmugmugAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        logger.error("Account %s not found", account_id)
        return

    try:
        client = await SmugmugClient.create(
            account.email, account.password, account.smugmug_nick
        )
        async with client:
            # Step 1: Fetch the full node tree
            nodes = await client.get_node_tree()

            # Step 2: Upsert folders and galleries
            _folder_uri_to_id, _gallery_data = await _upsert_nodes(db, account, nodes)

            # Step 3: Fetch and upsert images for each gallery
            # TODO: re-enable after node sync is tested
            # for gallery_id, album_id_str, album_key in gallery_data:
            #     if not album_id_str or not album_key:
            #         continue
            #     total_count, images = await client.get_album_images(
            #         album_id_str, album_key
            #     )
            #     await _upsert_images(db, gallery_id, images)
            #     await _update_gallery_image_count(db, gallery_id, total_count)

        # Step 4: Mark success
        now = datetime.now(UTC)
        account.sync_status = SmugmugSyncStatus.IDLE.value
        account.last_synced_at = now
        account.sync_error = None
        await db.flush()
        await db.commit()
        logger.info("Sync completed for account %s", account_id)

    except Exception:
        logger.exception("Sync failed for account %s", account_id)
        # Refresh in case session is dirty from the failed operations
        await db.rollback()
        # Re-fetch account after rollback
        result = await db.execute(
            select(SmugmugAccount).where(SmugmugAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if account is not None:
            account.sync_status = SmugmugSyncStatus.FAILED.value
            account.sync_error = "Sync failed — check server logs for details"
            await db.flush()
            await db.commit()


async def _upsert_nodes(
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
    # Load existing folders for this account
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
            # Should have been created above; re-fetch
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


async def _upsert_images(
    db: AsyncSession,
    gallery_id: uuid.UUID,
    images: list[dict[str, Any]],
) -> None:
    """Upsert images for a single gallery."""
    now = datetime.now(UTC)

    # Load existing images for this gallery
    existing_result = await db.execute(
        select(SmugmugImage).where(SmugmugImage.gallery_id == gallery_id)
    )
    existing = {img.smugmug_uri: img for img in existing_result.scalars().all()}

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

    await db.flush()


async def _update_gallery_image_count(
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
