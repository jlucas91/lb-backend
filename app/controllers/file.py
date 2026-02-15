import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.models.enums import FileType
from app.models.file import File
from app.schemas.file import FileConfirm, FileUpdate


def infer_file_type(content_type: str) -> str:
    if content_type.startswith("image/"):
        return FileType.PHOTO.value
    if content_type.startswith("video/"):
        return FileType.VIDEO.value
    if content_type in ("application/pdf",):
        return FileType.DOCUMENT.value
    return FileType.OTHER.value


def generate_presign(filename: str, content_type: str) -> tuple[str, str]:
    """Generate a dummy presigned URL and storage key."""
    storage_key = f"uploads/{uuid.uuid4()}/{filename}"
    upload_url = f"https://storage.example.com/{storage_key}?presigned=true"
    return upload_url, storage_key


async def confirm_upload(
    db: AsyncSession,
    location_id: uuid.UUID,
    data: FileConfirm,
    *,
    scouting_id: uuid.UUID | None = None,
) -> File:
    file = File(
        location_id=location_id,
        scouting_id=scouting_id,
        file_type=infer_file_type(data.content_type),
        storage_key=data.storage_key,
        filename=data.filename,
        content_type=data.content_type,
        size_bytes=data.size_bytes,
        caption=data.caption,
    )
    db.add(file)
    await db.flush()
    return file


async def list_files(
    db: AsyncSession,
    location_id: uuid.UUID,
    *,
    file_type: str | None = None,
    scouting_id: uuid.UUID | None = None,
) -> list[File]:
    query = (
        select(File)
        .where(File.location_id == location_id)
        .order_by(File.sort_order, File.created_at)
    )
    if scouting_id is not None:
        query = query.where(File.scouting_id == scouting_id)
    else:
        query = query.where(File.scouting_id.is_(None))
    if file_type:
        query = query.where(File.file_type == file_type)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_file(
    db: AsyncSession, file_id: uuid.UUID, location_id: uuid.UUID
) -> File:
    result = await db.execute(
        select(File).where(File.id == file_id, File.location_id == location_id)
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise not_found("File not found")
    return file


async def update_file(
    db: AsyncSession,
    file_id: uuid.UUID,
    location_id: uuid.UUID,
    data: FileUpdate,
) -> File:
    file = await get_file(db, file_id, location_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(file, key, value)
    await db.flush()
    return file


async def delete_file(
    db: AsyncSession, file_id: uuid.UUID, location_id: uuid.UUID
) -> None:
    file = await get_file(db, file_id, location_id)
    await db.delete(file)
    await db.flush()
