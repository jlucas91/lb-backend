import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.scouting import (
    create_scouting,
    delete_scouting,
    get_scouting,
    list_scoutings,
    update_scouting,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.scouting import (
    ScoutingCreate,
    ScoutingListResponse,
    ScoutingResponse,
    ScoutingUpdate,
)

router = APIRouter()


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
