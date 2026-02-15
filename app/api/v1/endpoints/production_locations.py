import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.production_location import (
    add_location,
    list_locations,
    remove_location,
    update_status,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.production import (
    ProductionLocationCreate,
    ProductionLocationResponse,
    ProductionLocationUpdate,
)

router = APIRouter()


@router.get(
    "/{production_id}/locations",
    response_model=list[ProductionLocationResponse],
)
async def list_production_locations(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductionLocationResponse]:
    locs = await list_locations(db, production_id, current_user)
    return [ProductionLocationResponse.model_validate(loc) for loc in locs]


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
) -> ProductionLocationResponse:
    pl = await add_location(db, production_id, current_user, data)
    await db.commit()
    return ProductionLocationResponse.model_validate(pl)


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
) -> ProductionLocationResponse:
    pl = await update_status(db, production_id, location_id, current_user, data)
    await db.commit()
    return ProductionLocationResponse.model_validate(pl)


@router.delete("/{production_id}/locations/{location_id}", status_code=204)
async def delete_production_location(
    production_id: uuid.UUID,
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_location(db, production_id, location_id, current_user)
    await db.commit()
