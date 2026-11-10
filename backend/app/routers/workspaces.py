from typing import List, Dict, Any
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
    WorkspaceRoleUpdate,
    OrganisationPublicOut,
    JoinWorkspaceRequest,
    JoinRequestOut,
    UserMembershipStatusOut,
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
    List all workspaces where the current user has explicit approved membership.
    """
    return workspace_service.list_workspaces_for_user(db, user=current_user)


@router.post(
    "/join",
    response_model=WorkspaceMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a request to join an existing organisation",
)
def join_organisation(
    payload: JoinWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a membership request using a valid ORG-XXXXXXXX identifier.
    Creates a pending membership request with requested role Employee.
    Users cannot access workspace data until approved by a workspace Admin.
    """
    try:
        member = workspace_service.request_join(
            db=db,
            org_id=payload.org_id,
            user_id=current_user.id,
        )
        return member
    except ValueError as val_err:
        err_msg = str(val_err)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in err_msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=err_msg)


@router.get(
    "/pending-requests",
    response_model=List[UserMembershipStatusOut],
    summary="List current user's submitted pending join requests",
)
def list_user_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns organisations the current user has requested to join that are awaiting approval.
    """
    return workspace_service.list_user_pending_requests(db, user=current_user)


@router.delete(
    "/pending-requests/{workspace_id}",
    summary="Cancel own pending join request",
)
def cancel_pending_request(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allows a user to cancel their own pending membership request.
    """
    try:
        workspace_service.cancel_join_request(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
        return {"success": True, "message": "Membership request cancelled."}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


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
    List all active approved members and their roles for the specified workspace.
    """
    members = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == "approved",
        )
        .all()
    )
    return members


@router.get(
    "/{workspace_id}/join-requests",
    response_model=List[JoinRequestOut],
    summary="List pending membership requests (Admin only)",
)
def list_pending_join_requests(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    """
    List all pending membership requests awaiting review in this organisation.
    Restricted strictly to workspace Admins.
    """
    return workspace_service.list_pending_requests(db, workspace_id=workspace_id)


@router.post(
    "/{workspace_id}/join-requests/{user_id}/approve",
    response_model=WorkspaceMemberOut,
    summary="Approve a member join request (Admin only)",
)
def approve_join_request(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: WorkspaceMember = Depends(require_workspace_admin),
    current_user: User = Depends(get_current_user),
):
    """
    Approve a pending membership request. The user receives active Employee access.
    Restricted strictly to workspace Admins.
    """
    try:
        return workspace_service.approve_request(
            db=db,
            workspace_id=workspace_id,
            target_user_id=user_id,
            admin_user=current_user,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/{workspace_id}/join-requests/{user_id}/reject",
    summary="Reject a member join request (Admin only)",
)
def reject_join_request(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: WorkspaceMember = Depends(require_workspace_admin),
    current_user: User = Depends(get_current_user),
):
    """
    Reject a pending membership request. Deletes the request so the user can re-apply if desired.
    Restricted strictly to workspace Admins.
    """
    try:
        workspace_service.reject_request(
            db=db,
            workspace_id=workspace_id,
            target_user_id=user_id,
            admin_user=current_user,
        )
        return {"success": True, "message": "Membership request rejected and removed."}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.patch(
    "/{workspace_id}/members/{user_id}/role",
    response_model=WorkspaceMemberOut,
    summary="Update member role between Employee and Reviewer (Admin only)",
)
def update_member_role(
    workspace_id: int,
    user_id: int,
    payload: WorkspaceRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: WorkspaceMember = Depends(require_workspace_admin),
    current_user: User = Depends(get_current_user),
):
    """
    Admin can promote Employee to Reviewer or demote Reviewer to Employee.
    Prevents self-demotion of the current Admin.
    Restricted strictly to workspace Admins.
    """
    try:
        return workspace_service.update_member_role(
            db=db,
            workspace_id=workspace_id,
            target_user_id=user_id,
            new_role=payload.role,
            admin_user=current_user,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
