import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.project_location import (
    compute_pages,
    copy_location_to_project,
    create_project_location,
    delete_project_location,
    get_project_location,
    list_project_locations,
    update_project_location,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.project_location import (
    ProjectLocationCopy,
    ProjectLocationCreate,
    ProjectLocationListResponse,
    ProjectLocationResponse,
    ProjectLocationUpdate,
)

router = APIRouter()


@router.get(
    "/{project_id}/locations",
    response_model=PaginatedResponse[ProjectLocationListResponse],
)
async def list_locations(
    project_id: uuid.UUID,
    location_type: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectLocationListResponse]:
    items, total = await list_project_locations(
        db,
        project_id,
        current_user,
        location_type=location_type,
        q=q,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        items=[ProjectLocationListResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=compute_pages(total, per_page),
    )


@router.post(
    "/{project_id}/locations",
    response_model=ProjectLocationResponse,
    status_code=201,
)
async def create(
    project_id: uuid.UUID,
    data: ProjectLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectLocationResponse:
    pl = await create_project_location(db, project_id, current_user, data)
    await db.commit()
    return ProjectLocationResponse.model_validate(pl)


@router.post(
    "/{project_id}/locations/copy",
    response_model=ProjectLocationResponse,
    status_code=201,
)
async def copy(
    project_id: uuid.UUID,
    data: ProjectLocationCopy,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectLocationResponse:
    pl = await copy_location_to_project(db, project_id, current_user, data.location_id)
    await db.commit()
    return ProjectLocationResponse.model_validate(pl)


@router.get(
    "/{project_id}/locations/{location_id}",
    response_model=ProjectLocationResponse,
)
async def get(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectLocationResponse:
    pl = await get_project_location(db, project_id, location_id, current_user)
    return ProjectLocationResponse.model_validate(pl)


@router.patch(
    "/{project_id}/locations/{location_id}",
    response_model=ProjectLocationResponse,
)
async def update(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    data: ProjectLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectLocationResponse:
    pl = await update_project_location(db, project_id, location_id, current_user, data)
    await db.commit()
    return ProjectLocationResponse.model_validate(pl)


@router.delete("/{project_id}/locations/{location_id}", status_code=204)
async def delete(
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_project_location(db, project_id, location_id, current_user)
    await db.commit()
