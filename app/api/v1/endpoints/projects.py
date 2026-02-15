import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.project import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_my_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    projs = await list_projects(db, current_user)
    return [ProjectResponse.model_validate(p) for p in projs]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    proj = await create_project(db, current_user, data)
    await db.commit()
    return ProjectResponse.model_validate(proj)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    proj = await get_project(db, project_id, current_user)
    return ProjectResponse.model_validate(proj)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    proj = await update_project(db, project_id, current_user, data)
    await db.commit()
    return ProjectResponse.model_validate(proj)


@router.delete("/{project_id}", status_code=204)
async def delete(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_project(db, project_id, current_user)
    await db.commit()
