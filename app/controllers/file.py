import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, not_found
from app.core.storage import S3StorageService
from app.models.enums import FileStatus, FileType
from app.models.file import File, Image
from app.schemas.file import ConfirmUpload, FileUpdate


def infer_file_category(content_type: str) -> str:
    if content_type.startswith("image/"):
        return FileType.PHOTO.value
    if content_type.startswith("video/"):
        return FileType.VIDEO.value
    if content_type in ("application/pdf",):
        return FileType.DOCUMENT.value
    return FileType.OTHER.value


async def request_upload(
    db: AsyncSession,
    storage: S3StorageService,
    user_id: uuid.UUID,
    filename: str,
    content_type: str,
) -> tuple[File, str]:
    storage_key = storage.generate_storage_key(filename)
    upload_url = await storage.generate_upload_url(storage_key, content_type)

    is_image = content_type.startswith("image/")
    file_cls = Image if is_image else File

    file = file_cls(
        uploaded_by_id=user_id,
        status=FileStatus.PENDING.value,
        file_category=infer_file_category(content_type),
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
    )
    db.add(file)
    await db.flush()
    return file, upload_url


async def confirm_upload(
    db: AsyncSession,
    storage: S3StorageService,
    user_id: uuid.UUID,
    file_id: uuid.UUID,
    data: ConfirmUpload,
) -> File:
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.uploaded_by_id == user_id,
            File.status == FileStatus.PENDING.value,
        )
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise not_found("File not found")

    meta = await storage.head_object(file.storage_key)
    file.size_bytes = meta.content_length
    file.status = FileStatus.ACTIVE.value

    if data.width is not None:
        file.width = data.width
    if data.height is not None:
        file.height = data.height

    await db.flush()
    await db.refresh(file)
    return file


async def get_file(
    db: AsyncSession,
    file_id: uuid.UUID,
    user_id: uuid.UUID,
) -> File:
    result = await db.execute(
        select(File).where(File.id == file_id, File.uploaded_by_id == user_id)
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise not_found("File not found")
    return file


async def update_file(
    db: AsyncSession,
    file_id: uuid.UUID,
    user_id: uuid.UUID,
    data: FileUpdate,
) -> File:
    file = await get_file(db, file_id, user_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(file, key, value)
    await db.flush()
    await db.refresh(file)
    return file


async def delete_file(
    db: AsyncSession,
    storage: S3StorageService,
    file_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    file = await get_file(db, file_id, user_id)
    if file.status != FileStatus.PENDING.value:
        await storage.delete_object(file.storage_key)
    await db.delete(file)
    await db.flush()


async def get_active_file(
    db: AsyncSession,
    file_id: uuid.UUID,
) -> File:
    """Get an ACTIVE file by ID (no ownership check)."""
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.status == FileStatus.ACTIVE.value,
        )
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise bad_request("File not found or not active")
    return file
