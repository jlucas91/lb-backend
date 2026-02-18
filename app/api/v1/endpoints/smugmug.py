import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.smugmug import (
    create_account,
    delete_account,
    get_account,
    get_folder_tree,
    get_gallery,
    get_gallery_images,
    list_accounts,
    list_galleries,
    trigger_sync,
    update_account,
)
from app.core.database import async_session, get_db
from app.models.user import User
from app.schemas.smugmug import (
    SmugmugAccountCreate,
    SmugmugAccountResponse,
    SmugmugAccountUpdate,
    SmugmugFolderTree,
    SmugmugGalleryDetailResponse,
    SmugmugGalleryResponse,
    SmugmugImageResponse,
)
from app.services.smugmug_sync import sync_account

router = APIRouter()


# --- Accounts ---


@router.post(
    "/accounts",
    response_model=SmugmugAccountResponse,
    status_code=201,
)
async def create(
    data: SmugmugAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmugmugAccountResponse:
    account = await create_account(db, current_user, data)
    await db.commit()
    return SmugmugAccountResponse.model_validate(account)


@router.get(
    "/accounts",
    response_model=list[SmugmugAccountResponse],
)
async def list_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SmugmugAccountResponse]:
    accounts = await list_accounts(db, current_user)
    return [SmugmugAccountResponse.model_validate(a) for a in accounts]


@router.get(
    "/accounts/{account_id}",
    response_model=SmugmugAccountResponse,
)
async def get(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmugmugAccountResponse:
    account = await get_account(db, current_user, account_id)
    return SmugmugAccountResponse.model_validate(account)


@router.patch(
    "/accounts/{account_id}",
    response_model=SmugmugAccountResponse,
)
async def update(
    account_id: uuid.UUID,
    data: SmugmugAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmugmugAccountResponse:
    account = await update_account(db, current_user, account_id, data)
    await db.commit()
    return SmugmugAccountResponse.model_validate(account)


@router.delete(
    "/accounts/{account_id}",
    status_code=204,
)
async def delete(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_account(db, current_user, account_id)
    await db.commit()


# --- Sync ---


@router.post(
    "/accounts/{account_id}/sync",
    response_model=SmugmugAccountResponse,
)
async def sync(
    account_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmugmugAccountResponse:
    account = await trigger_sync(db, current_user, account_id)
    await db.commit()

    async def _run_sync() -> None:
        async with async_session() as bg_db:
            await sync_account(bg_db, account_id)

    background_tasks.add_task(_run_sync)
    return SmugmugAccountResponse.model_validate(account)


# --- Folders ---


@router.get(
    "/accounts/{account_id}/folders",
    response_model=list[SmugmugFolderTree],
)
async def folders(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SmugmugFolderTree]:
    return await get_folder_tree(db, current_user, account_id)


# --- Galleries ---


@router.get(
    "/accounts/{account_id}/galleries",
    response_model=list[SmugmugGalleryResponse],
)
async def galleries(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SmugmugGalleryResponse]:
    gallery_list = await list_galleries(db, current_user, account_id)
    return [SmugmugGalleryResponse.model_validate(g) for g in gallery_list]


@router.get(
    "/galleries/{gallery_id}",
    response_model=SmugmugGalleryDetailResponse,
)
async def gallery_detail(
    gallery_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SmugmugGalleryDetailResponse:
    gallery = await get_gallery(db, current_user, gallery_id)
    images = await get_gallery_images(db, gallery_id)
    data = SmugmugGalleryResponse.model_validate(gallery).model_dump()
    data["images"] = [SmugmugImageResponse.model_validate(i) for i in images]
    return SmugmugGalleryDetailResponse(**data)
