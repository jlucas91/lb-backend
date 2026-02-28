"""Celery tasks for SmugMug sync fan-out.

sync_account_task  ─┬─ fetches node tree, upserts folders/galleries
                    └─ dispatches sync_gallery_task per gallery

sync_gallery_task  ─┬─ fetches images, upserts metadata
                    └─ dispatches download_image_task per new image

download_image_task ── downloads from CDN → S3 → creates File record
"""

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.storage import S3StorageService
from app.models.enums import SmugmugSyncStatus
from app.models.smugmug import SmugmugAccount
from app.services.smugmug_client import SmugmugClient
from app.services.smugmug_sync import (
    download_and_store_image,
    task_session,
    update_gallery_image_count,
    upsert_images,
    upsert_nodes,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="smugmug.sync_account")
def sync_account_task(account_id: str) -> None:
    """Login to SmugMug, sync the node tree, then fan out gallery tasks."""
    asyncio.run(_sync_account(account_id))


async def _sync_account(account_id: str) -> None:
    account_uuid = uuid.UUID(account_id)
    logger.info("[account:%s] Starting sync", account_id)
    t0 = time.monotonic()

    async with task_session() as db:
        result = await db.execute(
            select(SmugmugAccount).where(SmugmugAccount.id == account_uuid)
        )
        account = result.scalar_one_or_none()
        if account is None:
            logger.error("[account:%s] Account not found, aborting", account_id)
            return

        try:
            logger.info("[account:%s] Logging in as %s", account_id, account.email)
            client = await SmugmugClient.create(account.email, account.password)
            async with client:
                logger.info("[account:%s] Fetching node tree", account_id)
                nodes = await client.get_node_tree()
                logger.info(
                    "[account:%s] Fetched %d nodes, upserting",
                    account_id,
                    len(nodes),
                )
                _folder_uri_to_id, gallery_data = await upsert_nodes(db, account, nodes)
                session_cookie = client.session_cookie

            # Mark account idle after node tree sync
            now = datetime.now(UTC)
            account.sync_status = SmugmugSyncStatus.IDLE.value
            account.last_synced_at = now
            account.sync_error = None
            await db.flush()
            await db.commit()

            elapsed = time.monotonic() - t0
            logger.info(
                "[account:%s] Node tree synced in %.1fs — %d folders, %d galleries",
                account_id,
                elapsed,
                len(_folder_uri_to_id),
                len(gallery_data),
            )

        except Exception:
            logger.exception("[account:%s] Sync failed", account_id)
            await db.rollback()
            result = await db.execute(
                select(SmugmugAccount).where(SmugmugAccount.id == account_uuid)
            )
            account = result.scalar_one_or_none()
            if account is not None:
                account.sync_status = SmugmugSyncStatus.FAILED.value
                account.sync_error = "Sync failed — check server logs for details"
                await db.flush()
                await db.commit()
            return

    # Fan out gallery tasks (outside the session — fire and forget)
    dispatched = 0
    for gallery_id, album_id_str, album_key in gallery_data:
        if not album_id_str or not album_key:
            continue
        sync_gallery_task.delay(
            account_id,
            str(gallery_id),
            album_id_str,
            album_key,
            session_cookie,
        )
        dispatched += 1

    logger.info("[account:%s] Dispatched %d gallery sync tasks", account_id, dispatched)


@celery_app.task(name="smugmug.sync_gallery")
def sync_gallery_task(
    account_id: str,
    gallery_id: str,
    album_id: str,
    album_key: str,
    session_cookie: str,
) -> None:
    """Fetch images for one gallery, then fan out download tasks."""
    asyncio.run(
        _sync_gallery(account_id, gallery_id, album_id, album_key, session_cookie)
    )


async def _sync_gallery(
    account_id: str,
    gallery_id: str,
    album_id: str,
    album_key: str,
    session_cookie: str,
) -> None:
    gallery_uuid = uuid.UUID(gallery_id)
    logger.info(
        "[account:%s][gallery:%s] Fetching images (album %s)",
        account_id,
        gallery_id,
        album_key,
    )
    t0 = time.monotonic()

    client = SmugmugClient(session_cookie)
    async with client:
        total_count, images = await client.get_album_images(album_id, album_key)

    logger.info(
        "[account:%s][gallery:%s] Fetched %d images (total_count=%d), upserting",
        account_id,
        gallery_id,
        len(images),
        total_count,
    )

    async with task_session() as db:
        upserted = await upsert_images(db, gallery_uuid, images)
        await update_gallery_image_count(db, gallery_uuid, total_count)
        await db.commit()

        # Load user_id from the account for file ownership
        result = await db.execute(
            select(SmugmugAccount.user_id).where(
                SmugmugAccount.id == uuid.UUID(account_id)
            )
        )
        user_id = result.scalar_one()

    # Fan out download tasks for images without files
    needs_download = [img for img in upserted if img.file_id is None]
    for image in needs_download:
        download_image_task.delay(str(image.id), str(user_id))

    elapsed = time.monotonic() - t0
    logger.info(
        "[account:%s][gallery:%s] Done in %.1fs — %d upserted, %d downloads dispatched",
        account_id,
        gallery_id,
        elapsed,
        len(upserted),
        len(needs_download),
    )


@celery_app.task(name="smugmug.download_image")
def download_image_task(image_id: str, user_id: str) -> None:
    """Download a single image from CDN → S3."""
    asyncio.run(_download_image(image_id, user_id))


async def _download_image(image_id: str, user_id: str) -> None:
    logger.debug("[image:%s] Starting download", image_id)
    t0 = time.monotonic()
    storage = S3StorageService()
    async with task_session() as db:
        try:
            await download_and_store_image(
                db, uuid.UUID(image_id), uuid.UUID(user_id), storage
            )
            await db.commit()
            elapsed = time.monotonic() - t0
            logger.info("[image:%s] Downloaded and stored in %.1fs", image_id, elapsed)
        except Exception:
            logger.warning(
                "[image:%s] Download failed, skipping",
                image_id,
                exc_info=True,
            )
