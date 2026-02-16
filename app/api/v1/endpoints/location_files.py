import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file_attachment import attach_file, detach_file, list_entity_files
from app.controllers.location import _can_write_location, get_location_for_user
from app.core.database import get_db
from app.core.exceptions import forbidden
from app.core.storage import S3StorageService, get_storage
from app.models.location_file import LocationFile
from app.models.user import User
from app.schemas.file import AttachFileRequest, FileResponse

router = APIRouter()


@router.post(
    "/{location_id}/files",
    response_model=FileResponse,
    status_code=201,
)
async def attach_file_to_location(
    location_id: uuid.UUID,
    data: AttachFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> FileResponse:
    await get_location_for_user(db, location_id, current_user)
    if not await _can_write_location(db, location_id, current_user.id):
        raise forbidden("No write access to this location")
    await attach_file(db, data.file_id, LocationFile, location_id=location_id)
    await db.commit()
    # Return the file with download URL
    files = await list_entity_files(
        db, storage, LocationFile, LocationFile.location_id, location_id
    )
    for f in files:
        if f.id == data.file_id:
            return f
    return files[-1]


@router.get("/{location_id}/files", response_model=list[FileResponse])
async def list_location_files(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> list[FileResponse]:
    await get_location_for_user(db, location_id, current_user)
    return await list_entity_files(
        db, storage, LocationFile, LocationFile.location_id, location_id
    )


@router.delete("/{location_id}/files/{file_id}", status_code=204)
async def detach_file_from_location(
    location_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await get_location_for_user(db, location_id, current_user)
    if not await _can_write_location(db, location_id, current_user.id):
        raise forbidden("No write access to this location")
    await detach_file(db, file_id, LocationFile, LocationFile.location_id, location_id)
    await db.commit()
