import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.production import (
    create_production,
    delete_production,
    get_production,
    list_productions,
    update_production,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.production import (
    ProductionCreate,
    ProductionResponse,
    ProductionUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ProductionResponse])
async def list_my_productions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductionResponse]:
    prods = await list_productions(db, current_user)
    return [ProductionResponse.model_validate(p) for p in prods]


@router.post("", response_model=ProductionResponse, status_code=201)
async def create(
    data: ProductionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod = await create_production(db, current_user, data)
    await db.commit()
    return ProductionResponse.model_validate(prod)


@router.get("/{production_id}", response_model=ProductionResponse)
async def get(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod = await get_production(db, production_id, current_user)
    return ProductionResponse.model_validate(prod)


@router.patch("/{production_id}", response_model=ProductionResponse)
async def update(
    production_id: uuid.UUID,
    data: ProductionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod = await update_production(db, production_id, current_user, data)
    await db.commit()
    return ProductionResponse.model_validate(prod)


@router.delete("/{production_id}", status_code=204)
async def delete(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_production(db, production_id, current_user)
    await db.commit()
