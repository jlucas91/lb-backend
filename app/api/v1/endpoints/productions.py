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
from app.models.production import Production
from app.models.user import User
from app.schemas.production import (
    ProductionCreate,
    ProductionResponse,
    ProductionUpdate,
)

router = APIRouter()


def _to_response(prod: Production, role: str) -> ProductionResponse:
    data = {
        "id": prod.id,
        "name": prod.name,
        "description": prod.description,
        "status": prod.status,
        "my_role": role,
        "created_at": prod.created_at,
        "updated_at": prod.updated_at,
    }
    return ProductionResponse.model_validate(data)


@router.get("", response_model=list[ProductionResponse])
async def list_my_productions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductionResponse]:
    items = await list_productions(db, current_user)
    return [_to_response(prod, role) for prod, role in items]


@router.post("", response_model=ProductionResponse, status_code=201)
async def create(
    data: ProductionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod = await create_production(db, current_user, data)
    await db.commit()
    return _to_response(prod, "owner")


@router.get("/{production_id}", response_model=ProductionResponse)
async def get(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod, member = await get_production(db, production_id, current_user)
    return _to_response(prod, member.role)


@router.patch("/{production_id}", response_model=ProductionResponse)
async def update(
    production_id: uuid.UUID,
    data: ProductionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionResponse:
    prod, member = await update_production(db, production_id, current_user, data)
    await db.commit()
    return _to_response(prod, member.role)


@router.delete("/{production_id}", status_code=204)
async def delete(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_production(db, production_id, current_user)
    await db.commit()
