import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.controllers.project import require_manager_or_owner, require_member
from app.core.exceptions import bad_request, forbidden, not_found
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectMemberCreate, ProjectMemberUpdate


async def add_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    current_user: User,
    data: ProjectMemberCreate,
) -> ProjectMember | None:
    await require_manager_or_owner(db, project_id, current_user.id)
    # Look up user by email
    user_result = await db.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    if user is None:
        return None
    # Check if already a member
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None
    member = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=data.role.value,
    )
    db.add(member)
    await db.flush()
    # Re-fetch with user loaded
    result = await db.execute(
        select(ProjectMember)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
        .options(selectinload(ProjectMember.user))
    )
    return result.scalar_one()


async def list_members(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> list[ProjectMember]:
    await require_member(db, project_id, current_user.id)
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .options(selectinload(ProjectMember.user))
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
    # Re-fetch with user loaded
    result = await db.execute(
        select(ProjectMember)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        .options(selectinload(ProjectMember.user))
    )
    return result.scalar_one()


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
