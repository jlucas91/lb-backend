import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.episode import (
    create_episode,
    delete_episode,
    get_episode,
    list_episodes,
    update_episode,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.episode import EpisodeCreate, EpisodeResponse, EpisodeUpdate

router = APIRouter()


@router.get(
    "/{project_id}/episodes",
    response_model=list[EpisodeResponse],
)
async def list_project_episodes(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EpisodeResponse]:
    episodes = await list_episodes(db, project_id, current_user)
    return [EpisodeResponse.model_validate(e) for e in episodes]


@router.post(
    "/{project_id}/episodes",
    response_model=EpisodeResponse,
    status_code=201,
)
async def create(
    project_id: uuid.UUID,
    data: EpisodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    episode = await create_episode(db, project_id, current_user, data)
    await db.commit()
    return EpisodeResponse.model_validate(episode)


@router.get(
    "/{project_id}/episodes/{episode_id}",
    response_model=EpisodeResponse,
)
async def get(
    project_id: uuid.UUID,
    episode_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    episode = await get_episode(db, project_id, episode_id, current_user)
    return EpisodeResponse.model_validate(episode)


@router.patch(
    "/{project_id}/episodes/{episode_id}",
    response_model=EpisodeResponse,
)
async def update(
    project_id: uuid.UUID,
    episode_id: uuid.UUID,
    data: EpisodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    episode = await update_episode(db, project_id, episode_id, current_user, data)
    await db.commit()
    return EpisodeResponse.model_validate(episode)


@router.delete("/{project_id}/episodes/{episode_id}", status_code=204)
async def delete(
    project_id: uuid.UUID,
    episode_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_episode(db, project_id, episode_id, current_user)
    await db.commit()
