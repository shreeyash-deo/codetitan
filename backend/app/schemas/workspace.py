from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserOut


class WorkspaceBase(BaseModel):
    name: str


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceMemberCreate(BaseModel):
    user_id: int
    role: str = "Employee"


class WorkspaceRoleUpdate(BaseModel):
    role: str


class WorkspaceMemberOut(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceOut(WorkspaceBase):
    id: int
    org_id: str
    name: str
    created_at: datetime
    members: Optional[List[WorkspaceMemberOut]] = None

    model_config = ConfigDict(from_attributes=True)


class OrganisationPublicOut(BaseModel):
    name: str
    org_id: str

    model_config = ConfigDict(from_attributes=True)
