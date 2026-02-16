import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.production import (
    require_manager_or_owner,
    require_member,
)
from app.core.exceptions import conflict, not_found
from app.models.location import UserLocation
from app.models.production_location import ProductionLocation
from app.models.user import User
from app.schemas.production import (
    ProductionLocationCreate,
    ProductionLocationUpdate,
)


async def add_location(
    db: AsyncSession,
    production_id: uuid.UUID,
    current_user: User,
    data: ProductionLocationCreate,
) -> ProductionLocation:
    await require_member(db, production_id, current_user.id)
    existing = await db.execute(
        select(ProductionLocation).where(
            ProductionLocation.production_id == production_id,
            ProductionLocation.location_id == data.location_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("Location already in this production")
    pl = ProductionLocation(
        production_id=production_id,
        location_id=data.location_id,
        added_by_id=current_user.id,
        notes=data.notes,
    )
    db.add(pl)
    await db.flush()
    # Reload with relationships
    result = await db.execute(
        select(ProductionLocation)
        .where(
            ProductionLocation.production_id == production_id,
            ProductionLocation.location_id == data.location_id,
        )
        .options(
            selectinload(ProductionLocation.added_by),
            selectinload(ProductionLocation.location).selectinload(
                UserLocation.featured_file
            ),
        )
    )
    return result.scalar_one()


async def list_locations(
    db: AsyncSession, production_id: uuid.UUID, current_user: User
) -> list[ProductionLocation]:
    await require_member(db, production_id, current_user.id)
    result = await db.execute(
        select(ProductionLocation)
        .where(ProductionLocation.production_id == production_id)
        .options(
            selectinload(ProductionLocation.added_by),
            selectinload(ProductionLocation.location).selectinload(
                UserLocation.featured_file
            ),
        )
    )
    return list(result.scalars().all())


async def update_status(
    db: AsyncSession,
    production_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User,
    data: ProductionLocationUpdate,
) -> ProductionLocation:
    await require_manager_or_owner(db, production_id, current_user.id)
    result = await db.execute(
        select(ProductionLocation)
        .where(
            ProductionLocation.production_id == production_id,
            ProductionLocation.location_id == location_id,
        )
        .options(
            selectinload(ProductionLocation.added_by),
            selectinload(ProductionLocation.location).selectinload(
                UserLocation.featured_file
            ),
        )
    )
    pl = result.scalar_one_or_none()
    if pl is None:
        raise not_found("Production location not found")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    for key, value in update_data.items():
        setattr(pl, key, value)
    await db.flush()
    return pl


async def remove_location(
    db: AsyncSession,
    production_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User,
) -> None:
    await require_manager_or_owner(db, production_id, current_user.id)
    result = await db.execute(
        select(ProductionLocation).where(
            ProductionLocation.production_id == production_id,
            ProductionLocation.location_id == location_id,
        )
    )
    pl = result.scalar_one_or_none()
    if pl is None:
        raise not_found("Production location not found")
    await db.delete(pl)
    await db.flush()
