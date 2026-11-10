from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserOut


class WorkspaceBase(BaseModel):
    name: str


class WorkspaceCreate(WorkspaceBase):
    pass


class JoinWorkspaceRequest(BaseModel):
    org_id: str


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
    status: str = "approved"
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class JoinRequestOut(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    name: str
    email: str
    role: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class UserMembershipStatusOut(BaseModel):
    workspace_id: int
    org_id: str
    org_name: str
    role: str
    status: str


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
