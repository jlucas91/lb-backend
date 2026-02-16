import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.file import get_active_file
from app.core.exceptions import not_found
from app.core.storage import S3StorageService
from app.models.file import File
from app.schemas.file import FileResponse


async def attach_file(
    db: AsyncSession,
    file_id: uuid.UUID,
    link_model: type[Any],
    **link_kwargs: Any,
) -> None:
    """Attach an ACTIVE file to an entity via a join table."""
    await get_active_file(db, file_id)
    link = link_model(file_id=file_id, **link_kwargs)
    db.add(link)
    await db.flush()


async def list_entity_files(
    db: AsyncSession,
    storage: S3StorageService,
    link_model: type[Any],
    entity_fk_col: Any,
    entity_id: uuid.UUID,
) -> list[FileResponse]:
    """List files attached to an entity, with download URLs."""
    query = (
        select(File)
        .join(link_model, link_model.file_id == File.id)
        .where(entity_fk_col == entity_id)
        .order_by(File.sort_order, File.created_at)
    )
    result = await db.execute(query)
    files = list(result.scalars().all())

    responses = []
    for f in files:
        download_url = await storage.generate_download_url(f.storage_key)
        thumbnail_url = None
        if f.thumbnail_key:
            thumbnail_url = await storage.generate_download_url(f.thumbnail_key)
        resp = FileResponse.model_validate(f)
        resp.download_url = download_url
        resp.thumbnail_url = thumbnail_url
        responses.append(resp)
    return responses


async def detach_file(
    db: AsyncSession,
    file_id: uuid.UUID,
    link_model: type[Any],
    entity_fk_col: Any,
    entity_id: uuid.UUID,
) -> None:
    """Remove a file link from an entity (does NOT delete the file from S3)."""
    result = await db.execute(
        select(link_model).where(
            entity_fk_col == entity_id,
            link_model.file_id == file_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise not_found("File not attached to this entity")
    await db.delete(link)
    await db.flush()
