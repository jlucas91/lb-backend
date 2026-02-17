import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.user_folder import (
    create_user_folder,
    delete_user_folder,
    get_user_folder,
    list_user_folders,
    update_user_folder,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.user_folder import (
    UserFolderCreate,
    UserFolderResponse,
    UserFolderUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=list[UserFolderResponse],
)
async def list_folders(
    parent_id: uuid.UUID | None = Query(default=None),
    root_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserFolderResponse]:
    folders = await list_user_folders(
        db, current_user, parent_id=parent_id, root_only=root_only
    )
    return [UserFolderResponse.model_validate(f) for f in folders]


@router.post(
    "",
    response_model=UserFolderResponse,
    status_code=201,
)
async def create(
    data: UserFolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFolderResponse:
    folder = await create_user_folder(db, current_user, data)
    await db.commit()
    return UserFolderResponse.model_validate(folder)


@router.get(
    "/{folder_id}",
    response_model=UserFolderResponse,
)
async def get(
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFolderResponse:
    folder = await get_user_folder(db, folder_id, current_user)
    return UserFolderResponse.model_validate(folder)


@router.patch(
    "/{folder_id}",
    response_model=UserFolderResponse,
)
async def update(
    folder_id: uuid.UUID,
    data: UserFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserFolderResponse:
    folder = await update_user_folder(db, folder_id, current_user, data)
    await db.commit()
    return UserFolderResponse.model_validate(folder)


@router.delete("/{folder_id}", status_code=204)
async def delete(
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_user_folder(db, folder_id, current_user)
    await db.commit()
