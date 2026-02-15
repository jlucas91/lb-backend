import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, conflict, not_found
from app.models.location import Location
from app.models.location_share import LocationShare
from app.models.user import User
from app.schemas.location_share import LocationShareCreate


async def _require_owner(
    db: AsyncSession, location_id: uuid.UUID, user_id: uuid.UUID
) -> Location:
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.owner_id == user_id)
    )
    loc = result.scalar_one_or_none()
    if loc is None:
        raise not_found("Location not found or not owned by you")
    return loc


async def share_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    current_user: User,
    data: LocationShareCreate,
) -> LocationShare:
    await _require_owner(db, location_id, current_user.id)
    if data.shared_with_id == current_user.id:
        raise bad_request("Cannot share with yourself")
    existing = await db.execute(
        select(LocationShare).where(
            LocationShare.location_id == location_id,
            LocationShare.shared_with_id == data.shared_with_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("Already shared with this user")
    share = LocationShare(
        location_id=location_id,
        shared_by_id=current_user.id,
        shared_with_id=data.shared_with_id,
        permission=data.permission.value,
    )
    db.add(share)
    await db.flush()
    return share


async def list_shares(
    db: AsyncSession, location_id: uuid.UUID, current_user: User
) -> list[LocationShare]:
    await _require_owner(db, location_id, current_user.id)
    result = await db.execute(
        select(LocationShare).where(LocationShare.location_id == location_id)
    )
    return list(result.scalars().all())


async def revoke_share(
    db: AsyncSession,
    location_id: uuid.UUID,
    share_id: uuid.UUID,
    current_user: User,
) -> None:
    await _require_owner(db, location_id, current_user.id)
    result = await db.execute(
        select(LocationShare).where(
            LocationShare.id == share_id,
            LocationShare.location_id == location_id,
        )
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise not_found("Share not found")
    await db.delete(share)
    await db.flush()


async def list_shared_with_me(
    db: AsyncSession, current_user: User
) -> list[LocationShare]:
    result = await db.execute(
        select(LocationShare).where(LocationShare.shared_with_id == current_user.id)
    )
    return list(result.scalars().all())
