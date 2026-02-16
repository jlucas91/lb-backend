import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.controllers.project_member import (
    add_member,
    list_members,
    remove_member,
    update_role,
)
from app.core.database import get_db
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import (
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
)

router = APIRouter()


def _member_response(m: ProjectMember) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        project_id=m.project_id,
        user_id=m.user_id,
        display_name=m.user.display_name,
        email=m.user.email,
        role=m.role,
        joined_at=m.joined_at,
    )


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
async def list_project_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberResponse]:
    members = await list_members(db, project_id, current_user)
    return [_member_response(m) for m in members]


@router.post(
    "/{project_id}/members",
    status_code=201,
)
async def add_project_member(
    project_id: uuid.UUID,
    data: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await add_member(db, project_id, current_user, data)
    await db.commit()
    return {"message": "Member added"}


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
)
async def update_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    member = await update_role(db, project_id, user_id, current_user, data)
    await db.commit()
    return _member_response(member)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def delete_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_member(db, project_id, user_id, current_user)
    await db.commit()
