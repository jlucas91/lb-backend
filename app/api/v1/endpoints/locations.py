import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file_attachment import resolve_featured_image
from app.controllers.location import (
    compute_pages,
    create_location,
    delete_location,
    get_location_for_user,
    list_user_locations,
    update_location,
)
from app.core.database import get_db
from app.core.storage import S3StorageService, get_storage
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.location import (
    UserLocationCreate,
    UserLocationListResponse,
    UserLocationResponse,
    UserLocationUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserLocationListResponse])
async def list_locations(
    location_type: str | None = None,
    q: str | None = None,
    folder_id: uuid.UUID | None = Query(default=None),
    root_only: bool = Query(default=False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> PaginatedResponse[UserLocationListResponse]:
    items, total = await list_user_locations(
        db,
        current_user,
        location_type=location_type,
        q=q,
        folder_id=folder_id,
        root_only=root_only,
        page=page,
        per_page=per_page,
    )
    responses: list[UserLocationListResponse] = []
    for loc in items:
        resp = UserLocationListResponse.model_validate(loc)
        resp.featured_image = await resolve_featured_image(loc.featured_file, storage)
        responses.append(resp)
    return PaginatedResponse(
        items=responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=compute_pages(total, per_page),
    )


@router.post("", response_model=UserLocationResponse, status_code=201)
async def create(
    data: UserLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserLocationResponse:
    loc = await create_location(db, current_user, data)
    await db.commit()
    return UserLocationResponse.model_validate(loc)


@router.get("/{location_id}", response_model=UserLocationResponse)
async def get_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> UserLocationResponse:
    loc = await get_location_for_user(db, location_id, current_user)
    resp = UserLocationResponse.model_validate(loc)
    resp.featured_image = await resolve_featured_image(loc.featured_file, storage)
    return resp


@router.patch("/{location_id}", response_model=UserLocationResponse)
async def update(
    location_id: uuid.UUID,
    data: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> UserLocationResponse:
    loc = await update_location(db, location_id, current_user, data)
    await db.commit()
    resp = UserLocationResponse.model_validate(loc)
    resp.featured_image = await resolve_featured_image(loc.featured_file, storage)
    return resp


@router.delete("/{location_id}", status_code=204)
async def delete(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_location(db, location_id, current_user)
    await db.commit()
