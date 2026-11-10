from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, verify_workspace_access, require_workspace_admin
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceMemberCreate,
    WorkspaceMemberOut,
    OrganisationPublicOut,
)
from app.services.workspace_service import workspace_service
from app.services.auth_service import auth_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get(
    "/lookup",
    response_model=OrganisationPublicOut,
    summary="Public organisation lookup by Organisation ID",
)
def lookup_organisation(
    org_id: str = Query(..., description="Public Organisation ID (e.g. ORG-XXXXXXXX)"),
    db: Session = Depends(get_db),
):
    """
    Public organisation discovery endpoint.
    Exposes strictly the organisation name and org_id.
    Zero leakage of internal IDs, members, emails, or workspace assets.
    """
    workspace = workspace_service.get_by_org_id(db, org_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found.",
        )
    return OrganisationPublicOut(name=workspace.name, org_id=workspace.org_id)


@router.post(
    "",
    response_model=WorkspaceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
def create_workspace(
    workspace_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new brand workspace. The creator is automatically assigned as an Admin member.
    """
    workspace = workspace_service.create_workspace(
        db, workspace_in=workspace_in, creator_id=current_user.id
    )
    return workspace


@router.get(
    "",
    response_model=List[WorkspaceOut],
    summary="List accessible workspaces",
)
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all workspaces where the current user has explicit membership.
    """
    return workspace_service.list_workspaces_for_user(db, user=current_user)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceOut,
    summary="Get workspace details by ID",
)
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(verify_workspace_access),
):
    """
    Retrieve workspace details, verifying that the current user has access membership.
    """
    workspace = workspace_service.get_by_id(db, workspace_id=workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )
    return workspace


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a workspace member",
)
def add_workspace_member(
    workspace_id: int,
    member_in: WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    """
    Add or update a workspace member (Admin, Reviewer, Employee).
    Restricted strictly to workspace Admins.
    """
    target_user = auth_service.get_by_id(db, user_id=member_in.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user to add does not exist.",
        )

    try:
        membership = workspace_service.add_member(
            db=db,
            workspace_id=workspace_id,
            user_id=member_in.user_id,
            role=member_in.role,
        )
        return membership
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberOut],
    summary="List workspace members",
)
def list_workspace_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(verify_workspace_access),
):
    """
    List all members and their roles for the specified workspace.
    """
    members = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    return members
