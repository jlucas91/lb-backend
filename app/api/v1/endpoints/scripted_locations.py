import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.scripted_location import (
    add_scripted_location_location,
    create_scripted_location,
    delete_scripted_location,
    get_scripted_location,
    list_scripted_location_locations,
    list_scripted_locations,
    remove_scripted_location_location,
    update_scripted_location,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.scripted_location import (
    ScriptedLocationCreate,
    ScriptedLocationLocationCreate,
    ScriptedLocationLocationResponse,
    ScriptedLocationResponse,
    ScriptedLocationUpdate,
)

router = APIRouter()


# --- Scripted Location CRUD ---


@router.get(
    "/{project_id}/scripted-locations",
    response_model=list[ScriptedLocationResponse],
)
async def list_project_scripted_locations(
    project_id: uuid.UUID,
    episode_id: uuid.UUID | None = Query(default=None),
    folder_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScriptedLocationResponse]:
    items = await list_scripted_locations(
        db, project_id, current_user, episode_id=episode_id, folder_id=folder_id
    )
    return [ScriptedLocationResponse.model_validate(sl) for sl in items]


@router.post(
    "/{project_id}/scripted-locations",
    response_model=ScriptedLocationResponse,
    status_code=201,
)
async def create(
    project_id: uuid.UUID,
    data: ScriptedLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptedLocationResponse:
    sl = await create_scripted_location(db, project_id, current_user, data)
    await db.commit()
    return ScriptedLocationResponse.model_validate(sl)


@router.get(
    "/{project_id}/scripted-locations/{scripted_location_id}",
    response_model=ScriptedLocationResponse,
)
async def get(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptedLocationResponse:
    sl = await get_scripted_location(db, project_id, scripted_location_id, current_user)
    return ScriptedLocationResponse.model_validate(sl)


@router.patch(
    "/{project_id}/scripted-locations/{scripted_location_id}",
    response_model=ScriptedLocationResponse,
)
async def update(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    data: ScriptedLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptedLocationResponse:
    sl = await update_scripted_location(
        db, project_id, scripted_location_id, current_user, data
    )
    await db.commit()
    return ScriptedLocationResponse.model_validate(sl)


@router.delete(
    "/{project_id}/scripted-locations/{scripted_location_id}", status_code=204
)
async def delete(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_scripted_location(db, project_id, scripted_location_id, current_user)
    await db.commit()


# --- Scripted Location Locations ---


@router.get(
    "/{project_id}/scripted-locations/{scripted_location_id}/locations",
    response_model=list[ScriptedLocationLocationResponse],
)
async def list_locations(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScriptedLocationLocationResponse]:
    items = await list_scripted_location_locations(
        db, project_id, scripted_location_id, current_user
    )
    return [ScriptedLocationLocationResponse.model_validate(sll) for sll in items]


@router.post(
    "/{project_id}/scripted-locations/{scripted_location_id}/locations",
    response_model=ScriptedLocationLocationResponse,
    status_code=201,
)
async def add_location(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    data: ScriptedLocationLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptedLocationLocationResponse:
    sll = await add_scripted_location_location(
        db, project_id, scripted_location_id, current_user, data
    )
    await db.commit()
    return ScriptedLocationLocationResponse.model_validate(sll)


@router.delete(
    "/{project_id}/scripted-locations/{scripted_location_id}/locations/{location_id}",
    status_code=204,
)
async def remove_location(
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_scripted_location_location(
        db, project_id, scripted_location_id, location_id, current_user
    )
    await db.commit()
