import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.folder import (
    create_folder,
    delete_folder,
    get_folder,
    list_folders,
    update_folder,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate

router = APIRouter()


@router.get(
    "/{project_id}/folders",
    response_model=list[FolderResponse],
)
async def list_project_folders(
    project_id: uuid.UUID,
    parent_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FolderResponse]:
    folders = await list_folders(db, project_id, current_user, parent_id=parent_id)
    return [FolderResponse.model_validate(f) for f in folders]


@router.post(
    "/{project_id}/folders",
    response_model=FolderResponse,
    status_code=201,
)
async def create(
    project_id: uuid.UUID,
    data: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    folder = await create_folder(db, project_id, current_user, data)
    await db.commit()
    return FolderResponse.model_validate(folder)


@router.get(
    "/{project_id}/folders/{folder_id}",
    response_model=FolderResponse,
)
async def get(
    project_id: uuid.UUID,
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    folder = await get_folder(db, project_id, folder_id, current_user)
    return FolderResponse.model_validate(folder)


@router.patch(
    "/{project_id}/folders/{folder_id}",
    response_model=FolderResponse,
)
async def update(
    project_id: uuid.UUID,
    folder_id: uuid.UUID,
    data: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FolderResponse:
    folder = await update_folder(db, project_id, folder_id, current_user, data)
    await db.commit()
    return FolderResponse.model_validate(folder)


@router.delete("/{project_id}/folders/{folder_id}", status_code=204)
async def delete(
    project_id: uuid.UUID,
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_folder(db, project_id, folder_id, current_user)
    await db.commit()
