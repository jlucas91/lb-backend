import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.models.enums import SmugmugSyncStatus
from app.models.smugmug import (
    SmugmugAccount,
    SmugmugFolder,
    SmugmugGallery,
    SmugmugImage,
)
from app.models.user import User
from app.schemas.smugmug import (
    SmugmugAccountCreate,
    SmugmugAccountUpdate,
    SmugmugFolderTree,
    SmugmugGalleryResponse,
)

# --- Account helpers ---


async def _get_account_for_user(
    db: AsyncSession,
    account_id: uuid.UUID,
    user: User,
) -> SmugmugAccount:
    result = await db.execute(
        select(SmugmugAccount).where(
            SmugmugAccount.id == account_id,
            SmugmugAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise not_found("SmugMug account not found")
    return account


# --- Account CRUD ---


async def create_account(
    db: AsyncSession,
    user: User,
    data: SmugmugAccountCreate,
) -> SmugmugAccount:
    account = SmugmugAccount(
        user_id=user.id,
        email=data.email,
        password=data.password,
        sync_status=SmugmugSyncStatus.IDLE.value,
    )
    db.add(account)
    await db.flush()
    return account


async def list_accounts(
    db: AsyncSession,
    user: User,
) -> list[SmugmugAccount]:
    result = await db.execute(
        select(SmugmugAccount)
        .where(SmugmugAccount.user_id == user.id)
        .order_by(SmugmugAccount.created_at.desc())
    )
    return list(result.scalars().all())


async def get_account(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> SmugmugAccount:
    return await _get_account_for_user(db, account_id, user)


async def update_account(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
    data: SmugmugAccountUpdate,
) -> SmugmugAccount:
    account = await _get_account_for_user(db, account_id, user)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    await db.flush()
    await db.refresh(account)
    return account


async def delete_account(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> None:
    account = await _get_account_for_user(db, account_id, user)
    await db.delete(account)
    await db.flush()


# --- Sync ---


async def trigger_sync(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> SmugmugAccount:
    account = await _get_account_for_user(db, account_id, user)
    account.sync_status = SmugmugSyncStatus.SYNCING.value
    account.sync_error = None
    await db.flush()
    await db.refresh(account)
    # TODO: dispatch background sync task
    return account


# --- Folder tree ---


async def get_folder_tree(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> list[SmugmugFolderTree]:
    await _get_account_for_user(db, account_id, user)

    # Fetch all folders for this account
    folder_result = await db.execute(
        select(SmugmugFolder)
        .where(SmugmugFolder.account_id == account_id)
        .order_by(SmugmugFolder.sort_order, SmugmugFolder.name)
    )
    folders = list(folder_result.scalars().all())

    # Fetch all galleries for this account
    gallery_result = await db.execute(
        select(SmugmugGallery)
        .where(SmugmugGallery.account_id == account_id)
        .order_by(SmugmugGallery.sort_order, SmugmugGallery.name)
    )
    galleries = list(gallery_result.scalars().all())

    # Build gallery lookup by folder_id
    gallery_by_folder: dict[uuid.UUID | None, list[SmugmugGalleryResponse]] = {}
    for g in galleries:
        key = g.folder_id
        if key not in gallery_by_folder:
            gallery_by_folder[key] = []
        gallery_by_folder[key].append(SmugmugGalleryResponse.model_validate(g))

    # Build folder lookup by parent_id
    folder_by_parent: dict[uuid.UUID | None, list[SmugmugFolder]] = {}
    for f in folders:
        key = f.parent_id
        if key not in folder_by_parent:
            folder_by_parent[key] = []
        folder_by_parent[key].append(f)

    # Recursive builder
    def build_tree(parent_id: uuid.UUID | None) -> list[SmugmugFolderTree]:
        children = folder_by_parent.get(parent_id, [])
        return [
            SmugmugFolderTree(
                id=f.id,
                name=f.name,
                smugmug_uri=f.smugmug_uri,
                url_path=f.url_path,
                sort_order=f.sort_order,
                children=build_tree(f.id),
                galleries=gallery_by_folder.get(f.id, []),
            )
            for f in children
        ]

    return build_tree(None)


# --- Galleries ---


async def list_galleries(
    db: AsyncSession,
    user: User,
    account_id: uuid.UUID,
) -> list[SmugmugGallery]:
    await _get_account_for_user(db, account_id, user)
    result = await db.execute(
        select(SmugmugGallery)
        .where(SmugmugGallery.account_id == account_id)
        .order_by(SmugmugGallery.sort_order, SmugmugGallery.name)
    )
    return list(result.scalars().all())


async def get_gallery(
    db: AsyncSession,
    user: User,
    gallery_id: uuid.UUID,
) -> SmugmugGallery:
    result = await db.execute(
        select(SmugmugGallery).where(SmugmugGallery.id == gallery_id)
    )
    gallery = result.scalar_one_or_none()
    if gallery is None:
        raise not_found("Gallery not found")

    # Ownership check via account
    await _get_account_for_user(db, gallery.account_id, user)
    return gallery


async def get_gallery_images(
    db: AsyncSession,
    gallery_id: uuid.UUID,
) -> list[SmugmugImage]:
    result = await db.execute(
        select(SmugmugImage)
        .where(SmugmugImage.gallery_id == gallery_id)
        .order_by(SmugmugImage.filename)
    )
    return list(result.scalars().all())
