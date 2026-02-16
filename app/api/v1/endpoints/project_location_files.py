import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file_attachment import attach_file, detach_file, list_entity_files
from app.controllers.project_location import get_project_location
from app.core.database import get_db
from app.core.storage import S3StorageService, get_storage
from app.models.file import File
from app.models.project_location_file import ProjectLocationFile
from app.models.user import User
from app.schemas.file import AttachFileRequest, FileResponse

router = APIRouter()


@router.post(
    "/{project_id}/locations/{location_id}/files",
    response_model=FileResponse,
    status_code=201,
)
async def attach_file_to_project_location(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    data: AttachFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> FileResponse:
    pl = await get_project_location(db, project_id, location_id, current_user)
    await attach_file(db, data.file_id, ProjectLocationFile, project_location_id=pl.id)
    # Auto-set featured image on first photo attach
    if pl.featured_file_id is None:
        file_result = await db.execute(select(File).where(File.id == data.file_id))
        file = file_result.scalar_one_or_none()
        if file and file.file_category == "photo":
            pl.featured_file_id = data.file_id
            await db.flush()
    await db.commit()
    files = await list_entity_files(
        db,
        storage,
        ProjectLocationFile,
        ProjectLocationFile.project_location_id,
        pl.id,
    )
    for f in files:
        if f.id == data.file_id:
            return f
    return files[-1]


@router.get(
    "/{project_id}/locations/{location_id}/files",
    response_model=list[FileResponse],
)
async def list_project_location_files(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> list[FileResponse]:
    pl = await get_project_location(db, project_id, location_id, current_user)
    return await list_entity_files(
        db,
        storage,
        ProjectLocationFile,
        ProjectLocationFile.project_location_id,
        pl.id,
    )


@router.delete(
    "/{project_id}/locations/{location_id}/files/{file_id}",
    status_code=204,
)
async def detach_file_from_project_location(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    pl = await get_project_location(db, project_id, location_id, current_user)
    await detach_file(
        db,
        file_id,
        ProjectLocationFile,
        ProjectLocationFile.project_location_id,
        pl.id,
    )
    if pl.featured_file_id == file_id:
        pl.featured_file_id = None
        await db.flush()
    await db.commit()
