import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, not_found
from app.models.production import Production
from app.models.production_member import ProductionMember
from app.models.user import User
from app.schemas.production import ProductionCreate, ProductionUpdate


async def create_production(
    db: AsyncSession, creator: User, data: ProductionCreate
) -> Production:
    prod = Production(name=data.name, description=data.description)
    db.add(prod)
    await db.flush()
    member = ProductionMember(production_id=prod.id, user_id=creator.id, role="owner")
    db.add(member)
    await db.flush()
    return prod


async def require_member(
    db: AsyncSession, production_id: uuid.UUID, user_id: uuid.UUID
) -> ProductionMember:
    result = await db.execute(
        select(ProductionMember).where(
            ProductionMember.production_id == production_id,
            ProductionMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise not_found("Production not found")
    return member


async def require_manager_or_owner(
    db: AsyncSession, production_id: uuid.UUID, user_id: uuid.UUID
) -> ProductionMember:
    member = await require_member(db, production_id, user_id)
    if member.role not in ("owner", "manager"):
        raise forbidden("Requires owner or manager role")
    return member


async def get_production(
    db: AsyncSession, production_id: uuid.UUID, user: User
) -> tuple[Production, ProductionMember]:
    member = await require_member(db, production_id, user.id)
    result = await db.execute(select(Production).where(Production.id == production_id))
    prod = result.scalar_one_or_none()
    if prod is None:
        raise not_found("Production not found")
    return prod, member


async def list_productions(
    db: AsyncSession, user: User
) -> list[tuple[Production, str]]:
    query = (
        select(Production, ProductionMember.role)
        .join(
            ProductionMember,
            Production.id == ProductionMember.production_id,
        )
        .where(ProductionMember.user_id == user.id)
        .order_by(Production.created_at.desc())
    )
    result = await db.execute(query)
    return [(row[0], row[1]) for row in result.all()]


async def update_production(
    db: AsyncSession,
    production_id: uuid.UUID,
    user: User,
    data: ProductionUpdate,
) -> tuple[Production, ProductionMember]:
    member = await require_manager_or_owner(db, production_id, user.id)
    result = await db.execute(select(Production).where(Production.id == production_id))
    prod = result.scalar_one_or_none()
    if prod is None:
        raise not_found("Production not found")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    for key, value in update_data.items():
        setattr(prod, key, value)
    await db.flush()
    await db.refresh(prod)
    return prod, member


async def delete_production(
    db: AsyncSession, production_id: uuid.UUID, user: User
) -> None:
    member = await require_member(db, production_id, user.id)
    if member.role != "owner":
        raise forbidden("Only the owner can delete a production")
    result = await db.execute(select(Production).where(Production.id == production_id))
    prod = result.scalar_one_or_none()
    if prod is None:
        raise not_found("Production not found")
    await db.delete(prod)
    await db.flush()
