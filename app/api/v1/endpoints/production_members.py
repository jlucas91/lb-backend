import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.production_member import (
    add_member,
    list_members,
    remove_member,
    update_role,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.production import (
    ProductionMemberCreate,
    ProductionMemberResponse,
    ProductionMemberUpdate,
)

router = APIRouter()


@router.get(
    "/{production_id}/members",
    response_model=list[ProductionMemberResponse],
)
async def list_production_members(
    production_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProductionMemberResponse]:
    members = await list_members(db, production_id, current_user)
    return [ProductionMemberResponse.model_validate(m) for m in members]


@router.post(
    "/{production_id}/members",
    response_model=ProductionMemberResponse,
    status_code=201,
)
async def add_production_member(
    production_id: uuid.UUID,
    data: ProductionMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionMemberResponse:
    member = await add_member(db, production_id, current_user, data)
    await db.commit()
    return ProductionMemberResponse.model_validate(member)


@router.patch(
    "/{production_id}/members/{user_id}",
    response_model=ProductionMemberResponse,
)
async def update_member_role(
    production_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ProductionMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductionMemberResponse:
    member = await update_role(db, production_id, user_id, current_user, data)
    await db.commit()
    return ProductionMemberResponse.model_validate(member)


@router.delete("/{production_id}/members/{user_id}", status_code=204)
async def delete_production_member(
    production_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_member(db, production_id, user_id, current_user)
    await db.commit()
