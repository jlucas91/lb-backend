import math
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.location import get_location_for_user
from app.controllers.project import require_member
from app.core.exceptions import not_found
from app.models.project_location import ProjectLocation
from app.models.user import User
from app.schemas.project_location import (
    ProjectLocationCreate,
    ProjectLocationUpdate,
)


async def create_project_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    data: ProjectLocationCreate,
) -> ProjectLocation:
    await require_member(db, project_id, user.id)
    pl = ProjectLocation(
        project_id=project_id,
        added_by_id=user.id,
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
    db.add(pl)
    await db.flush()
    return pl


async def copy_location_to_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    source_location_id: uuid.UUID,
) -> ProjectLocation:
    await require_member(db, project_id, user.id)
    # Verify user has read access to the source location
    source = await get_location_for_user(db, source_location_id, user)
    pl = ProjectLocation(
        project_id=project_id,
        added_by_id=user.id,
        source_location_id=source.id,
        name=source.name,
        address=source.address,
        city=source.city,
        state=source.state,
        country=source.country,
        latitude=source.latitude,
        longitude=source.longitude,
        location_type=source.location_type,
        description=source.description,
    )
    db.add(pl)
    await db.flush()
    return pl


async def list_project_locations(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    *,
    location_type: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ProjectLocation], int]:
    await require_member(db, project_id, user.id)
    query = select(ProjectLocation).where(ProjectLocation.project_id == project_id)
    if location_type:
        query = query.where(ProjectLocation.location_type == location_type)
    if q:
        pattern = f"%{q}%"
        query = query.where(
            or_(
                ProjectLocation.name.ilike(pattern),
                ProjectLocation.address.ilike(pattern),
                ProjectLocation.description.ilike(pattern),
            )
        )
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(ProjectLocation.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


async def get_project_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    user: User,
) -> ProjectLocation:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(ProjectLocation).where(
            ProjectLocation.id == location_id,
            ProjectLocation.project_id == project_id,
        )
    )
    pl = result.scalar_one_or_none()
    if pl is None:
        raise not_found("Project location not found")
    return pl


async def update_project_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    user: User,
    data: ProjectLocationUpdate,
) -> ProjectLocation:
    pl = await get_project_location(db, project_id, location_id, user)
    update_data = data.model_dump(exclude_unset=True)
    if "location_type" in update_data and update_data["location_type"] is not None:
        update_data["location_type"] = update_data["location_type"].value
    for key, value in update_data.items():
        setattr(pl, key, value)
    await db.flush()
    await db.refresh(pl)
    return pl


async def delete_project_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    location_id: uuid.UUID,
    user: User,
) -> None:
    pl = await get_project_location(db, project_id, location_id, user)
    await db.delete(pl)
    await db.flush()


def compute_pages(total: int, per_page: int) -> int:
    return max(1, math.ceil(total / per_page))
