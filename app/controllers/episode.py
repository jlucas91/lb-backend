import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.project import require_manager_or_owner, require_member
from app.core.exceptions import not_found
from app.models.episode import Episode
from app.models.user import User
from app.schemas.episode import EpisodeCreate, EpisodeUpdate


async def create_episode(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    data: EpisodeCreate,
) -> Episode:
    await require_manager_or_owner(db, project_id, user.id)
    episode = Episode(
        project_id=project_id,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(episode)
    await db.flush()
    return episode


async def list_episodes(
    db: AsyncSession, project_id: uuid.UUID, user: User
) -> list[Episode]:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(Episode)
        .where(Episode.project_id == project_id)
        .order_by(Episode.sort_order, Episode.created_at)
    )
    return list(result.scalars().all())


async def get_episode(
    db: AsyncSession, project_id: uuid.UUID, episode_id: uuid.UUID, user: User
) -> Episode:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_id, Episode.project_id == project_id
        )
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise not_found("Episode not found")
    return episode


async def update_episode(
    db: AsyncSession,
    project_id: uuid.UUID,
    episode_id: uuid.UUID,
    user: User,
    data: EpisodeUpdate,
) -> Episode:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_id, Episode.project_id == project_id
        )
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise not_found("Episode not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(episode, key, value)
    await db.flush()
    await db.refresh(episode)
    return episode


async def delete_episode(
    db: AsyncSession, project_id: uuid.UUID, episode_id: uuid.UUID, user: User
) -> None:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(Episode).where(
            Episode.id == episode_id, Episode.project_id == project_id
        )
    )
    episode = result.scalar_one_or_none()
    if episode is None:
        raise not_found("Episode not found")
    await db.delete(episode)
    await db.flush()
