import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.file_attachment import resolve_featured_image
from app.controllers.production_location import (
    add_location,
    list_locations,
    remove_location,
    update_status,
)
from app.core.database import get_db
from app.core.storage import S3StorageService, get_storage
from app.models.production_location import ProductionLocation
from app.models.user import User
from app.schemas.production import (
    ProductionLocationAddedBy,
    ProductionLocationCreate,
    ProductionLocationLocationSummary,
    ProductionLocationResponse,
    ProductionLocationUpdate,
)

router = APIRouter()


async def _to_response(
    pl: ProductionLocation, storage: S3StorageService
) -> ProductionLocationResponse:
    loc = pl.location
    featured_image = (
        await resolve_featured_image(loc.featured_file, storage) if loc else None
    )
    return ProductionLocationResponse(
        production_id=pl.production_id,
        location_id=pl.location_id,
        added_by_id=pl.added_by_id,
        status=pl.status,
        notes=pl.notes,
        added_by=ProductionLocationAddedBy.model_validate(pl.added_by),
        location=ProductionLocationLocationSummary(
            id=loc.id,
            owner_id=loc.owner_id,
            address=loc.address,
            name=loc.name,
            city=loc.city,
            state=loc.state,
            country=loc.country,
            location_type=loc.location_type,
            featured_image=featured_image,
            created_at=loc.created_at,
        ),
        added_at=pl.added_at,
    )


@router.get(
    "/{production_id}/locations",
    response_model=list[ProductionLocationResponse],
)
async def list_production_locations(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> list[ProductionLocationResponse]:
    locs = await list_locations(db, production_id, current_user)
    return [await _to_response(loc, storage) for loc in locs]


@router.post(
    "/{production_id}/locations",
    response_model=ProductionLocationResponse,
    status_code=201,
)
async def add_production_location(
    production_id: uuid.UUID,
    data: ProductionLocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> ProductionLocationResponse:
    pl = await add_location(db, production_id, current_user, data)
    await db.commit()
    return await _to_response(pl, storage)


@router.patch(
    "/{production_id}/locations/{location_id}",
    response_model=ProductionLocationResponse,
)
async def update_production_location(
    production_id: uuid.UUID,
    location_id: uuid.UUID,
    data: ProductionLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: S3StorageService = Depends(get_storage),
) -> ProductionLocationResponse:
    pl = await update_status(db, production_id, location_id, current_user, data)
    await db.commit()
    return await _to_response(pl, storage)


@router.delete("/{production_id}/locations/{location_id}", status_code=204)
async def delete_production_location(
    production_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_location(db, production_id, location_id, current_user)
    await db.commit()
