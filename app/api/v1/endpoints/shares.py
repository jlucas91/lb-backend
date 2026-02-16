import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file_attachment import resolve_featured_image
from app.controllers.location_share import (
    list_shared_with_me,
    list_shares,
    revoke_share,
    share_location,
)
from app.core.database import get_db
from app.core.storage import S3StorageService, get_storage
from app.models.user import User
from app.schemas.location_share import (
    LocationShareCreate,
    LocationShareListResponse,
    LocationShareResponse,
    SharedLocationDetailResponse,
)

router = APIRouter()


@router.post(
    "/{location_id}/shares",
    response_model=LocationShareResponse,
    status_code=201,
)
async def create_share(
    location_id: uuid.UUID,
    data: LocationShareCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationShareResponse:
    share = await share_location(db, location_id, current_user, data)
    await db.commit()
    return LocationShareResponse.model_validate(share)


@router.get(
    "/{location_id}/shares",
    response_model=list[LocationShareListResponse],
)
async def list_location_shares(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LocationShareListResponse]:
    shares = await list_shares(db, location_id, current_user)
    return [LocationShareListResponse.model_validate(s) for s in shares]


@router.delete("/{location_id}/shares/{share_id}", status_code=204)
async def delete_share(
    location_id: uuid.UUID,
    share_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await revoke_share(db, location_id, share_id, current_user)
    await db.commit()


shared_with_me_router = APIRouter()


@shared_with_me_router.get(
    "/shared-with-me", response_model=list[SharedLocationDetailResponse]
)
async def get_shared_with_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> list[SharedLocationDetailResponse]:
    shares = await list_shared_with_me(db, current_user)
    results: list[SharedLocationDetailResponse] = []
    for s in shares:
        loc = s.location
        featured = await resolve_featured_image(
            loc.featured_file if loc else None, storage
        )
        data = {
            "id": s.id,
            "location_id": s.location_id,
            "shared_by_id": s.shared_by_id,
            "shared_with_id": s.shared_with_id,
            "permission": s.permission,
            "created_at": s.created_at,
            "location": {
                "id": loc.id,
                "name": loc.name,
                "address": loc.address,
                "city": loc.city,
                "state": loc.state,
                "country": loc.country,
                "location_type": loc.location_type,
                "featured_image": featured,
            }
            if loc
            else None,
            "shared_by": {
                "id": s.shared_by.id,
                "display_name": s.shared_by.display_name,
            }
            if s.shared_by
            else None,
        }
        results.append(SharedLocationDetailResponse.model_validate(data))
    return results
