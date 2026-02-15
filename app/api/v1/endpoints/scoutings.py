import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file import (
    confirm_upload,
    delete_file,
    generate_presign,
    list_files,
)
from app.controllers.scouting import (
    create_scouting,
    delete_scouting,
    get_scouting,
    list_scoutings,
    update_scouting,
)
from app.core.database import get_db
from app.core.exceptions import forbidden
from app.models.user import User
from app.schemas.file import (
    FileConfirm,
    FileResponse,
    PresignRequest,
    PresignResponse,
)
from app.schemas.scouting import (
    ScoutingCreate,
    ScoutingListResponse,
    ScoutingResponse,
    ScoutingUpdate,
)

router = APIRouter()


# --- Scouting CRUD ---


@router.post(
    "/{location_id}/scoutings",
    response_model=ScoutingResponse,
    status_code=201,
)
async def create(
    location_id: uuid.UUID,
    data: ScoutingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoutingResponse:
    scouting = await create_scouting(db, location_id, current_user, data)
    await db.commit()
    return ScoutingResponse.model_validate(scouting)


@router.get(
    "/{location_id}/scoutings",
    response_model=list[ScoutingListResponse],
)
async def list_all(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScoutingListResponse]:
    scoutings = await list_scoutings(db, location_id, current_user)
    return [ScoutingListResponse.model_validate(s) for s in scoutings]


@router.get(
    "/{location_id}/scoutings/{scouting_id}",
    response_model=ScoutingResponse,
)
async def get(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoutingResponse:
    scouting = await get_scouting(db, location_id, scouting_id, current_user)
    return ScoutingResponse.model_validate(scouting)


@router.patch(
    "/{location_id}/scoutings/{scouting_id}",
    response_model=ScoutingResponse,
)
async def update(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    data: ScoutingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScoutingResponse:
    scouting = await update_scouting(db, location_id, scouting_id, current_user, data)
    await db.commit()
    return ScoutingResponse.model_validate(scouting)


@router.delete(
    "/{location_id}/scoutings/{scouting_id}",
    status_code=204,
)
async def delete(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_scouting(db, location_id, scouting_id, current_user)
    await db.commit()


# --- Scouting Photos ---


@router.post(
    "/{location_id}/scoutings/{scouting_id}/photos/presign",
    response_model=PresignResponse,
)
async def photo_presign(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    data: PresignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresignResponse:
    scouting = await get_scouting(db, location_id, scouting_id, current_user)
    if scouting.scouted_by_id != current_user.id:
        raise forbidden("Only the scout can upload photos")
    upload_url, storage_key = generate_presign(data.filename, data.content_type)
    return PresignResponse(upload_url=upload_url, storage_key=storage_key)


@router.post(
    "/{location_id}/scoutings/{scouting_id}/photos/confirm",
    response_model=FileResponse,
    status_code=201,
)
async def photo_confirm(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    data: FileConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    scouting = await get_scouting(db, location_id, scouting_id, current_user)
    if scouting.scouted_by_id != current_user.id:
        raise forbidden("Only the scout can upload photos")
    file = await confirm_upload(db, location_id, data, scouting_id=scouting_id)
    await db.commit()
    return FileResponse.model_validate(file)


@router.get(
    "/{location_id}/scoutings/{scouting_id}/photos",
    response_model=list[FileResponse],
)
async def list_photos(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileResponse]:
    await get_scouting(db, location_id, scouting_id, current_user)
    files = await list_files(db, location_id, scouting_id=scouting_id)
    return [FileResponse.model_validate(f) for f in files]


@router.delete(
    "/{location_id}/scoutings/{scouting_id}/photos/{file_id}",
    status_code=204,
)
async def delete_photo(
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    scouting = await get_scouting(db, location_id, scouting_id, current_user)
    if scouting.scouted_by_id != current_user.id:
        raise forbidden("Only the scout can delete photos")
    await delete_file(db, file_id, location_id)
    await db.commit()
