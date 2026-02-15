import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.location import (
    compute_pages,
    create_location,
    delete_location,
    get_location_for_user,
    list_user_locations,
    update_location,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.location import (
    LocationCreate,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LocationListResponse])
async def list_locations(
    location_type: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[LocationListResponse]:
    items, total = await list_user_locations(
        db, current_user, location_type=location_type, q=q, page=page, per_page=per_page
    )
    return PaginatedResponse(
        items=[LocationListResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=compute_pages(total, per_page),
    )


@router.post("", response_model=LocationResponse, status_code=201)
async def create(
    data: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    loc = await create_location(db, current_user, data)
    await db.commit()
    return LocationResponse.model_validate(loc)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    loc = await get_location_for_user(db, location_id, current_user)
    return LocationResponse.model_validate(loc)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update(
    location_id: uuid.UUID,
    data: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    loc = await update_location(db, location_id, current_user, data)
    await db.commit()
    return LocationResponse.model_validate(loc)


@router.delete("/{location_id}", status_code=204)
async def delete(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_location(db, location_id, current_user)
    await db.commit()
