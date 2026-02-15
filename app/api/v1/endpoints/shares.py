import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.location_share import (
    list_shared_with_me,
    list_shares,
    revoke_share,
    share_location,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.location_share import LocationShareCreate, LocationShareResponse

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
    response_model=list[LocationShareResponse],
)
async def list_location_shares(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LocationShareResponse]:
    shares = await list_shares(db, location_id, current_user)
    return [LocationShareResponse.model_validate(s) for s in shares]


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
    "/shared-with-me", response_model=list[LocationShareResponse]
)
async def get_shared_with_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LocationShareResponse]:
    shares = await list_shared_with_me(db, current_user)
    return [LocationShareResponse.model_validate(s) for s in shares]
