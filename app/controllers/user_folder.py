import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, not_found
from app.models.user import User
from app.models.user_folder import UserFolder
from app.schemas.user_folder import UserFolderCreate, UserFolderUpdate


async def _validate_parent(
    db: AsyncSession, owner_id: uuid.UUID, parent_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(UserFolder).where(
            UserFolder.id == parent_id, UserFolder.owner_id == owner_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise bad_request("Parent folder not found")


async def create_user_folder(
    db: AsyncSession,
    user: User,
    data: UserFolderCreate,
) -> UserFolder:
    if data.parent_id is not None:
        await _validate_parent(db, user.id, data.parent_id)
    folder = UserFolder(
        owner_id=user.id,
        parent_id=data.parent_id,
        name=data.name,
        sort_order=data.sort_order,
    )
    db.add(folder)
    await db.flush()
    return folder


async def list_user_folders(
    db: AsyncSession,
    user: User,
    *,
    parent_id: uuid.UUID | None = None,
    root_only: bool = False,
) -> list[UserFolder]:
    query = select(UserFolder).where(UserFolder.owner_id == user.id)
    if root_only:
        query = query.where(UserFolder.parent_id.is_(None))
    elif parent_id is not None:
        query = query.where(UserFolder.parent_id == parent_id)
    query = query.order_by(UserFolder.sort_order, UserFolder.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_folder(
    db: AsyncSession, folder_id: uuid.UUID, user: User
) -> UserFolder:
    result = await db.execute(
        select(UserFolder).where(
            UserFolder.id == folder_id, UserFolder.owner_id == user.id
        )
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise not_found("Folder not found")
    return folder


async def update_user_folder(
    db: AsyncSession,
    folder_id: uuid.UUID,
    user: User,
    data: UserFolderUpdate,
) -> UserFolder:
    folder = await get_user_folder(db, folder_id, user)
    update_data = data.model_dump(exclude_unset=True)
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        if update_data["parent_id"] == folder_id:
            raise bad_request("A folder cannot be its own parent")
        await _validate_parent(db, user.id, update_data["parent_id"])
    for key, value in update_data.items():
        setattr(folder, key, value)
    await db.flush()
    await db.refresh(folder)
    return folder


async def delete_user_folder(
    db: AsyncSession, folder_id: uuid.UUID, user: User
) -> None:
    folder = await get_user_folder(db, folder_id, user)
    await db.delete(folder)
    await db.flush()
