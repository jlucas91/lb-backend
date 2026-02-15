import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ProjectRole, ProjectStatus, ProjectType


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    project_type: ProjectType


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    project_type: ProjectType | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    project_type: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: ProjectRole = ProjectRole.MEMBER


class ProjectMemberUpdate(BaseModel):
    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime | None = None

    model_config = {"from_attributes": True}
