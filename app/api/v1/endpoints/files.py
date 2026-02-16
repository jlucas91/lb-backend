import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file import (
    confirm_upload,
    delete_file,
    get_file,
    request_upload,
    update_file,
)
from app.core.database import get_db
from app.core.storage import S3StorageService, get_storage
from app.models.user import User
from app.schemas.file import (
    ConfirmUpload,
    FileResponse,
    FileUpdate,
    UploadRequest,
    UploadResponse,
)

router = APIRouter()


@router.post("/request-upload", response_model=UploadResponse, status_code=201)
async def request_upload_endpoint(
    data: UploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> UploadResponse:
    file, upload_url = await request_upload(
        db, storage, current_user.id, data.filename, data.content_type
    )
    await db.commit()
    return UploadResponse(
        file_id=file.id,
        upload_url=upload_url,
        storage_key=file.storage_key,
    )


@router.post("/{file_id}/confirm", response_model=FileResponse)
async def confirm_upload_endpoint(
    file_id: uuid.UUID,
    data: ConfirmUpload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> FileResponse:
    file = await confirm_upload(db, storage, current_user.id, file_id, data)
    await db.commit()
    return FileResponse.model_validate(file)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_endpoint(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> FileResponse:
    file = await get_file(db, file_id, current_user.id)
    download_url = await storage.generate_download_url(file.storage_key)
    resp = FileResponse.model_validate(file)
    resp.download_url = download_url
    if file.thumbnail_key:
        resp.thumbnail_url = await storage.generate_download_url(file.thumbnail_key)
    return resp


@router.patch("/{file_id}", response_model=FileResponse)
async def update_file_endpoint(
    file_id: uuid.UUID,
    data: FileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file = await update_file(db, file_id, current_user.id, data)
    await db.commit()
    return FileResponse.model_validate(file)


@router.delete("/{file_id}", status_code=204)
async def delete_file_endpoint(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> None:
    await delete_file(db, storage, file_id, current_user.id)
    await db.commit()
