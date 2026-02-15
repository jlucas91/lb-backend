import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file import (
    confirm_upload,
    delete_file,
    generate_presign,
    list_files,
    update_file,
)
from app.controllers.location import get_location_for_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.file import (
    FileConfirm,
    FileResponse,
    FileUpdate,
    PresignRequest,
    PresignResponse,
)

router = APIRouter()


@router.post("/{location_id}/files/presign", response_model=PresignResponse)
async def presign(
    location_id: uuid.UUID,
    data: PresignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresignResponse:
    await get_location_for_user(db, location_id, current_user)
    upload_url, storage_key = generate_presign(data.filename, data.content_type)
    return PresignResponse(upload_url=upload_url, storage_key=storage_key)


@router.post(
    "/{location_id}/files/confirm",
    response_model=FileResponse,
    status_code=201,
)
async def confirm(
    location_id: uuid.UUID,
    data: FileConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await get_location_for_user(db, location_id, current_user)
    file = await confirm_upload(db, location_id, data)
    await db.commit()
    return FileResponse.model_validate(file)


@router.get("/{location_id}/files", response_model=list[FileResponse])
async def list_location_files(
    location_id: uuid.UUID,
    file_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileResponse]:
    await get_location_for_user(db, location_id, current_user)
    files = await list_files(db, location_id, file_type=file_type)
    return [FileResponse.model_validate(f) for f in files]


@router.patch("/{location_id}/files/{file_id}", response_model=FileResponse)
async def update(
    location_id: uuid.UUID,
    file_id: uuid.UUID,
    data: FileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await get_location_for_user(db, location_id, current_user)
    file = await update_file(db, file_id, location_id, data)
    await db.commit()
    return FileResponse.model_validate(file)


@router.delete("/{location_id}/files/{file_id}", status_code=204)
async def delete(
    location_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await get_location_for_user(db, location_id, current_user)
    await delete_file(db, file_id, location_id)
    await db.commit()
