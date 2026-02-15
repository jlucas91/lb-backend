import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.project import require_manager_or_owner, require_member
from app.core.exceptions import bad_request, conflict, forbidden, not_found
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectMemberCreate, ProjectMemberUpdate


async def add_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    current_user: User,
    data: ProjectMemberCreate,
) -> ProjectMember:
    await require_manager_or_owner(db, project_id, current_user.id)
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise conflict("User is already a member")
    member = ProjectMember(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role.value,
    )
    db.add(member)
    await db.flush()
    return member


async def list_members(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> list[ProjectMember]:
    await require_member(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    return list(result.scalars().all())


async def update_role(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User,
    data: ProjectMemberUpdate,
) -> ProjectMember:
    current_member = await require_member(db, project_id, current_user.id)
    if current_member.role != "owner":
        raise forbidden("Only the owner can change roles")
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise not_found("Member not found")
    if target.user_id == current_user.id:
        raise bad_request("Cannot change your own role")
    target.role = data.role.value
    await db.flush()
    return target


async def remove_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User,
) -> None:
    await require_manager_or_owner(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise not_found("Member not found")
    if target.role == "owner":
        raise bad_request("Cannot remove the owner")
    await db.delete(target)
    await db.flush()
