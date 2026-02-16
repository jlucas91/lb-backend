import math
import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.location import UserLocation
from app.models.location_file import LocationFile
from app.models.location_share import LocationShare
from app.models.production_location import ProductionLocation
from app.models.production_member import ProductionMember
from app.models.user import User
from app.schemas.location import UserLocationCreate, UserLocationUpdate


async def create_location(
    db: AsyncSession, owner: User, data: UserLocationCreate
) -> UserLocation:
    loc = UserLocation(
        owner_id=owner.id,
        name=data.name,
        address=data.address,
        city=data.city,
        state=data.state,
        country=data.country,
        latitude=data.latitude,
        longitude=data.longitude,
        location_type=data.location_type.value if data.location_type else None,
        description=data.description,
    )
    db.add(loc)
    await db.flush()
    return loc


def _accessible_locations_query(user_id: uuid.UUID) -> Select[tuple[UserLocation]]:
    """Build a query for locations the user can read."""
    shared_ids = (
        select(LocationShare.location_id)
        .where(LocationShare.shared_with_id == user_id)
        .correlate(None)
    )
    production_ids = (
        select(ProductionLocation.location_id)
        .join(
            ProductionMember,
            ProductionLocation.production_id == ProductionMember.production_id,
        )
        .where(ProductionMember.user_id == user_id)
        .correlate(None)
    )
    return (
        select(UserLocation)
        .options(joinedload(UserLocation.featured_file))
        .where(
            or_(
                UserLocation.owner_id == user_id,
                UserLocation.id.in_(shared_ids),
                UserLocation.id.in_(production_ids),
            )
        )
    )


async def get_location_for_user(
    db: AsyncSession, location_id: uuid.UUID, user: User
) -> UserLocation:
    query = _accessible_locations_query(user.id).where(UserLocation.id == location_id)
    result = await db.execute(query)
    loc = result.unique().scalar_one_or_none()
    if loc is None:
        raise not_found("Location not found")
    return loc


async def _can_write_location(
    db: AsyncSession, location_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(UserLocation).where(
            UserLocation.id == location_id, UserLocation.owner_id == user_id
        )
    )
    if result.scalar_one_or_none() is not None:
        return True
    share_result = await db.execute(
        select(LocationShare).where(
            LocationShare.location_id == location_id,
            LocationShare.shared_with_id == user_id,
            LocationShare.permission == "edit",
        )
    )
    return share_result.scalar_one_or_none() is not None


async def list_user_locations(
    db: AsyncSession,
    user: User,
    *,
    location_type: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[UserLocation], int]:
    query = _accessible_locations_query(user.id)
    if location_type:
        query = query.where(UserLocation.location_type == location_type)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                UserLocation.name.ilike(pattern),
                UserLocation.address.ilike(pattern),
                UserLocation.description.ilike(pattern),
            )
        )
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(UserLocation.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = list(result.unique().scalars().all())
    return items, total


async def update_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    user: User,
    data: UserLocationUpdate,
) -> UserLocation:
    loc = await get_location_for_user(db, location_id, user)
    if not await _can_write_location(db, location_id, user.id):
        raise forbidden("No write access to this location")
    update_data = data.model_dump(exclude_unset=True)
    if "location_type" in update_data and update_data["location_type"] is not None:
        update_data["location_type"] = update_data["location_type"].value
    # Validate featured_file_id is attached to this location
    if (
        "featured_file_id" in update_data
        and update_data["featured_file_id"] is not None
    ):
        fid = update_data["featured_file_id"]
        link_result = await db.execute(
            select(LocationFile).where(
                LocationFile.location_id == location_id,
                LocationFile.file_id == fid,
            )
        )
        if link_result.scalar_one_or_none() is None:
            raise bad_request("File is not attached to this location")
    for key, value in update_data.items():
        setattr(loc, key, value)
    await db.flush()
    await db.refresh(loc)
    return loc


async def delete_location(db: AsyncSession, location_id: uuid.UUID, user: User) -> None:
    result = await db.execute(
        select(UserLocation).where(
            UserLocation.id == location_id, UserLocation.owner_id == user.id
        )
    )
    loc = result.scalar_one_or_none()
    if loc is None:
        raise not_found("Location not found or not owned by you")
    await db.delete(loc)
    await db.flush()


def compute_pages(total: int, per_page: int) -> int:
    return max(1, math.ceil(total / per_page))
