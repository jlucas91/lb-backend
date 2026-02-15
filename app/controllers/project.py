import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import forbidden, not_found
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(
    db: AsyncSession, creator: User, data: ProjectCreate
) -> Project:
    proj = Project(
        name=data.name,
        description=data.description,
        project_type=data.project_type.value,
    )
    db.add(proj)
    await db.flush()
    member = ProjectMember(project_id=proj.id, user_id=creator.id, role="owner")
    db.add(member)
    await db.flush()
    return proj


async def require_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember:
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise not_found("Project not found")
    return member


async def require_manager_or_owner(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember:
    member = await require_member(db, project_id, user_id)
    if member.role not in ("owner", "manager"):
        raise forbidden("Requires owner or manager role")
    return member


async def get_project(db: AsyncSession, project_id: uuid.UUID, user: User) -> Project:
    await require_member(db, project_id, user.id)
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if proj is None:
        raise not_found("Project not found")
    return proj


async def list_projects(db: AsyncSession, user: User) -> list[Project]:
    query = (
        select(Project)
        .join(
            ProjectMember,
            Project.id == ProjectMember.project_id,
        )
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    data: ProjectUpdate,
) -> Project:
    await require_manager_or_owner(db, project_id, user.id)
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if proj is None:
        raise not_found("Project not found")
    update_data = data.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = update_data["status"].value
    if "project_type" in update_data and update_data["project_type"] is not None:
        update_data["project_type"] = update_data["project_type"].value
    for key, value in update_data.items():
        setattr(proj, key, value)
    await db.flush()
    await db.refresh(proj)
    return proj


async def delete_project(db: AsyncSession, project_id: uuid.UUID, user: User) -> None:
    member = await require_member(db, project_id, user.id)
    if member.role != "owner":
        raise forbidden("Only the owner can delete a project")
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if proj is None:
        raise not_found("Project not found")
    await db.delete(proj)
    await db.flush()
