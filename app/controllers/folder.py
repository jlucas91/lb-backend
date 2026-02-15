import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.project import require_manager_or_owner, require_member
from app.core.exceptions import bad_request, not_found
from app.models.folder import Folder
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate


async def _validate_parent(
    db: AsyncSession, project_id: uuid.UUID, parent_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Folder).where(Folder.id == parent_id, Folder.project_id == project_id)
    )
    if result.scalar_one_or_none() is None:
        raise bad_request("Parent folder not found in this project")


async def create_folder(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    data: FolderCreate,
) -> Folder:
    await require_manager_or_owner(db, project_id, user.id)
    if data.parent_id is not None:
        await _validate_parent(db, project_id, data.parent_id)
    folder = Folder(
        project_id=project_id,
        parent_id=data.parent_id,
        name=data.name,
        sort_order=data.sort_order,
    )
    db.add(folder)
    await db.flush()
    return folder


async def list_folders(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    *,
    parent_id: uuid.UUID | None = None,
    root_only: bool = False,
) -> list[Folder]:
    await require_member(db, project_id, user.id)
    query = select(Folder).where(Folder.project_id == project_id)
    if root_only:
        query = query.where(Folder.parent_id.is_(None))
    elif parent_id is not None:
        query = query.where(Folder.parent_id == parent_id)
    query = query.order_by(Folder.sort_order, Folder.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_folder(
    db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID, user: User
) -> Folder:
    await require_member(db, project_id, user.id)
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.project_id == project_id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise not_found("Folder not found")
    return folder


async def update_folder(
    db: AsyncSession,
    project_id: uuid.UUID,
    folder_id: uuid.UUID,
    user: User,
    data: FolderUpdate,
) -> Folder:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.project_id == project_id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise not_found("Folder not found")
    update_data = data.model_dump(exclude_unset=True)
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        if update_data["parent_id"] == folder_id:
            raise bad_request("A folder cannot be its own parent")
        await _validate_parent(db, project_id, update_data["parent_id"])
    for key, value in update_data.items():
        setattr(folder, key, value)
    await db.flush()
    await db.refresh(folder)
    return folder


async def delete_folder(
    db: AsyncSession, project_id: uuid.UUID, folder_id: uuid.UUID, user: User
) -> None:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.project_id == project_id)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise not_found("Folder not found")
    await db.delete(folder)
    await db.flush()
