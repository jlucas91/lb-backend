import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.location import get_location_for_user
from app.core.exceptions import forbidden, not_found
from app.models.location import UserLocation
from app.models.scouting import Scouting
from app.models.user import User
from app.schemas.scouting import ScoutingCreate, ScoutingUpdate


async def create_scouting(
    db: AsyncSession,
    location_id: uuid.UUID,
    user: User,
    data: ScoutingCreate,
) -> Scouting:
    await get_location_for_user(db, location_id, user)
    scouting = Scouting(
        location_id=location_id,
        scouted_by_id=user.id,
        notes=data.notes,
        scouted_at=data.scouted_at,
        status=data.status.value,
    )
    db.add(scouting)
    await db.flush()
    return scouting


async def list_scoutings(
    db: AsyncSession,
    location_id: uuid.UUID,
    user: User,
) -> list[Scouting]:
    await get_location_for_user(db, location_id, user)
    result = await db.execute(
        select(Scouting)
        .where(Scouting.location_id == location_id)
        .order_by(Scouting.scouted_at.desc())
    )
    return list(result.scalars().all())


async def get_scouting(
    db: AsyncSession,
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    user: User,
) -> Scouting:
    await get_location_for_user(db, location_id, user)
    result = await db.execute(
        select(Scouting).where(
            Scouting.id == scouting_id,
            Scouting.location_id == location_id,
        )
    )
    scouting = result.scalar_one_or_none()
    if scouting is None:
        raise not_found("Scouting not found")
    return scouting


async def update_scouting(
    db: AsyncSession,
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    user: User,
    data: ScoutingUpdate,
) -> Scouting:
    scouting = await get_scouting(db, location_id, scouting_id, user)
    if scouting.scouted_by_id != user.id:
        raise forbidden("Only the scout can edit this scouting")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    for key, value in update_data.items():
        setattr(scouting, key, value)
    await db.flush()
    await db.refresh(scouting)
    return scouting


async def delete_scouting(
    db: AsyncSession,
    location_id: uuid.UUID,
    scouting_id: uuid.UUID,
    user: User,
) -> None:
    scouting = await get_scouting(db, location_id, scouting_id, user)
    # Scout OR location owner can delete
    if scouting.scouted_by_id != user.id:
        result = await db.execute(
            select(UserLocation).where(
                UserLocation.id == location_id, UserLocation.owner_id == user.id
            )
        )
        if result.scalar_one_or_none() is None:
            raise forbidden("Only the scout or location owner can delete this scouting")
    await db.delete(scouting)
    await db.flush()
