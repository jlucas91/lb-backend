import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.controllers.project import require_manager_or_owner, require_member
from app.core.exceptions import bad_request, conflict, not_found
from app.models.episode import Episode
from app.models.folder import Folder
from app.models.project_location import ProjectLocation
from app.models.scripted_location import ScriptedLocation
from app.models.scripted_location_location import ScriptedLocationLocation
from app.models.user import User
from app.schemas.scripted_location import (
    ScriptedLocationCreate,
    ScriptedLocationLocationCreate,
    ScriptedLocationUpdate,
)


async def _validate_episode(
    db: AsyncSession, project_id: uuid.UUID, episode_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_id, Episode.project_id == project_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise bad_request("Episode not found in this project")


async def _validate_folder(
    db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.project_id == project_id)
    )
    if result.scalar_one_or_none() is None:
        raise bad_request("Folder not found in this project")


async def create_scripted_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    data: ScriptedLocationCreate,
) -> ScriptedLocation:
    await require_manager_or_owner(db, project_id, user.id)
    if data.episode_id is not None:
        await _validate_episode(db, project_id, data.episode_id)
    if data.folder_id is not None:
        await _validate_folder(db, project_id, data.folder_id)
    sl = ScriptedLocation(
        project_id=project_id,
        episode_id=data.episode_id,
        folder_id=data.folder_id,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(sl)
    await db.flush()
    return sl


async def list_scripted_locations(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    *,
    episode_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
) -> list[ScriptedLocation]:
    await require_member(db, project_id, user.id)
    query = (
        select(ScriptedLocation)
        .options(joinedload(ScriptedLocation.featured_file))
        .where(ScriptedLocation.project_id == project_id)
    )
    if episode_id is not None:
        query = query.where(ScriptedLocation.episode_id == episode_id)
    if folder_id is not None:
        query = query.where(ScriptedLocation.folder_id == folder_id)
    query = query.order_by(ScriptedLocation.sort_order, ScriptedLocation.created_at)
    result = await db.execute(query)
    return list(result.unique().scalars().all())


async def get_scripted_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    user: User,
) -> ScriptedLocation:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(ScriptedLocation)
        .options(joinedload(ScriptedLocation.featured_file))
        .where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    sl = result.unique().scalar_one_or_none()
    if sl is None:
        raise not_found("Scripted location not found")
    return sl


async def update_scripted_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    user: User,
    data: ScriptedLocationUpdate,
) -> ScriptedLocation:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(ScriptedLocation)
        .options(joinedload(ScriptedLocation.featured_file))
        .where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    sl = result.unique().scalar_one_or_none()
    if sl is None:
        raise not_found("Scripted location not found")
    update_data = data.model_dump(exclude_unset=True)
    if "episode_id" in update_data and update_data["episode_id"] is not None:
        await _validate_episode(db, project_id, update_data["episode_id"])
    if "folder_id" in update_data and update_data["folder_id"] is not None:
        await _validate_folder(db, project_id, update_data["folder_id"])
    for key, value in update_data.items():
        setattr(sl, key, value)
    await db.flush()
    await db.refresh(sl)
    return sl


async def delete_scripted_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    user: User,
) -> None:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(ScriptedLocation).where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    sl = result.scalar_one_or_none()
    if sl is None:
        raise not_found("Scripted location not found")
    await db.delete(sl)
    await db.flush()


# --- Scripted Location Locations ---


async def add_scripted_location_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    user: User,
    data: ScriptedLocationLocationCreate,
) -> ScriptedLocationLocation:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(ScriptedLocation).where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise not_found("Scripted location not found")
    # Validate project_location belongs to this project
    pl_result = await db.execute(
        select(ProjectLocation).where(
            ProjectLocation.id == data.project_location_id,
            ProjectLocation.project_id == project_id,
        )
    )
    if pl_result.scalar_one_or_none() is None:
        raise not_found("Project location not found in this project")
    existing = await db.execute(
        select(ScriptedLocationLocation).where(
            ScriptedLocationLocation.scripted_location_id == scripted_location_id,
            ScriptedLocationLocation.project_location_id == data.project_location_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("Location already in this scripted location")
    sll = ScriptedLocationLocation(
        scripted_location_id=scripted_location_id,
        project_location_id=data.project_location_id,
        added_by_id=user.id,
        notes=data.notes,
    )
    db.add(sll)
    await db.flush()
    # Re-fetch with relationships for response serialization
    sll_result = await db.execute(
        select(ScriptedLocationLocation)
        .where(
            ScriptedLocationLocation.scripted_location_id == scripted_location_id,
            ScriptedLocationLocation.project_location_id == data.project_location_id,
        )
        .options(
            selectinload(ScriptedLocationLocation.project_location).joinedload(
                ProjectLocation.featured_file
            ),
            selectinload(ScriptedLocationLocation.added_by),
        )
    )
    return sll_result.unique().scalar_one()


async def list_scripted_location_locations(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    user: User,
) -> list[ScriptedLocationLocation]:
    await require_member(db, project_id, user.id)
    sl_result = await db.execute(
        select(ScriptedLocation).where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    if sl_result.scalar_one_or_none() is None:
        raise not_found("Scripted location not found")
    result = await db.execute(
        select(ScriptedLocationLocation)
        .where(ScriptedLocationLocation.scripted_location_id == scripted_location_id)
        .options(
            selectinload(ScriptedLocationLocation.project_location).joinedload(
                ProjectLocation.featured_file
            ),
            selectinload(ScriptedLocationLocation.added_by),
        )
    )
    return list(result.unique().scalars().all())


async def remove_scripted_location_location(
    db: AsyncSession,
    project_id: uuid.UUID,
    scripted_location_id: uuid.UUID,
    project_location_id: uuid.UUID,
    user: User,
) -> None:
    await require_manager_or_owner(db, project_id, user.id)
    sl_result = await db.execute(
        select(ScriptedLocation).where(
            ScriptedLocation.id == scripted_location_id,
            ScriptedLocation.project_id == project_id,
        )
    )
    if sl_result.scalar_one_or_none() is None:
        raise not_found("Scripted location not found")
    result = await db.execute(
        select(ScriptedLocationLocation).where(
            ScriptedLocationLocation.scripted_location_id == scripted_location_id,
            ScriptedLocationLocation.project_location_id == project_location_id,
        )
    )
    sll = result.scalar_one_or_none()
    if sll is None:
        raise not_found("Location not in this scripted location")
    await db.delete(sll)
    await db.flush()
