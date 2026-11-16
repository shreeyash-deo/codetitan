from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import verify_workspace_access, get_current_user, get_workspace_member
from app.models.approval import Approval
from app.models.review import ContentReview
from app.models.rule import BrandRule
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalOut,
    RequestApprovalPayload,
    RequestChangesPayload,
    RejectApprovalPayload,
)
from app.services.approval_service import approval_service
from app.services.workspace_service import workspace_service

router = APIRouter(tags=["Approvals & Governance Workflow"])


def _verify_approval_access(
    db: Session,
    approval: Approval,
    current_user: User,
    require_decision_role: bool = False,
):
    """
    Ensure user has access to the workspace and item of this approval.
    - Resolves workspace_id from approval.
    - Validates underlying review or brand rule relationship.
    - Verifies user has active approved membership in that workspace.
    - If user is an Employee (or Editor):
      - Must only retrieve approval records where approval.submitted_by == current_user.id.
      - Cannot perform decision actions (approve, reject, request-changes).
    - If user is Reviewer or Admin:
      - Has workspace-wide approval access within that workspace.
      - Can perform permitted approval decisions within that workspace.
    - Prevents cross-workspace access or access when membership is revoked.
    """
    ws_id = approval_service.get_approval_workspace_id(db, approval)
    if ws_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval item is not associated with a valid workspace.",
        )

    # Validate underlying review or brand rule relationship
    if approval.review_id:
        review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
        if not review or review.workspace_id != ws_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying content review not found in workspace.",
            )
    elif approval.brand_rule_id:
        rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
        if not rule or rule.workspace_id != ws_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying brand rule not found in workspace.",
            )

    # Check active/approved membership in the workspace
    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == ws_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.status == "approved",
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have access to this approval item.",
        )

    user_role = member.role.lower()

    if require_decision_role:
        if user_role not in ("admin", "reviewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted. Required workspace role: Reviewer or Admin",
            )
        if approval.brand_rule_id and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted. Required workspace role: Admin",
            )

    # Employee isolation: Employees may only retrieve their own submissions
    if user_role in ("employee", "editor"):
        if approval.submitted_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Employees can only access their own approval submissions.",
            )


# ============================================================================
# APPROVAL REQUEST ENDPOINTS
# ============================================================================

@router.post(
    "/reviews/{review_id}/request-approval",
    response_model=ApprovalOut,
    status_code=status.HTTP_201_CREATED,
    summary="Request reviewer sign-off for a content review",
)
def request_review_approval(
    review_id: int,
    payload: Optional[RequestApprovalPayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a content review for managerial / compliance sign-off."""
    review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content review not found.")
    member = workspace_service.get_member(db, review.workspace_id, current_user.id)
    if not member or member.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the workspace for this review.",
        )
    if member.role.lower() in ("employee", "editor") and review.submitted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Employees can only request approval for their own reviews.",
        )

    comment = payload.comment if payload else None
    summary = payload.summary if payload else None
    reviewer_id = payload.reviewer_id if payload else None
    try:
        approval = approval_service.request_review_approval(
            db=db,
            review_id=review_id,
            user=current_user,
            comment=comment,
            reviewer_id=reviewer_id,
            submission_summary=summary,
        )
        return approval
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/rules/{rule_id}/request-approval",
    response_model=ApprovalOut,
    status_code=status.HTTP_201_CREATED,
    summary="Request sign-off for a proposed brand rule",
)
def request_rule_approval(
    rule_id: int,
    payload: Optional[RequestApprovalPayload] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a brand rule for sign-off as official brand knowledge."""
    rule = db.query(BrandRule).filter(BrandRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand rule not found.")
    member = workspace_service.get_member(db, rule.workspace_id, current_user.id)
    if not member or member.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the workspace for this rule.",
        )
    comment = payload.comment if payload else None
    reviewer_id = payload.reviewer_id if payload else None
    try:
        approval = approval_service.request_rule_approval(
            db=db,
            rule_id=rule_id,
            user=current_user,
            comment=comment,
            reviewer_id=reviewer_id,
        )
        return approval
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ============================================================================
# WORKSPACE APPROVAL QUEUE
# ============================================================================

@router.get(
    "/workspaces/{workspace_id}/approvals",
    response_model=List[ApprovalOut],
    summary="List approval requests for a workspace",
)
def list_workspace_approvals(
    workspace_id: int,
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, changes_requested)"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
    _: int = Depends(verify_workspace_access),
):
    """Retrieve all pending and processed approval tickets for this workspace, scoped to user for Employees."""
    is_employee = bool(member and member.role.lower() in ("employee", "editor"))
    submitted_by = current_user.id if is_employee else None
    return approval_service.list_workspace_approvals(
        db=db, workspace_id=workspace_id, status=status, submitted_by=submitted_by
    )


@router.post(
    "/workspaces/{workspace_id}/approvals",
    response_model=ApprovalOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request in workspace",
)
def create_workspace_approval(
    workspace_id: int,
    approval_in: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: int = Depends(verify_workspace_access),
):
    """Legacy/workspace-scoped approval request creation."""
    if approval_in.review_id:
        review = db.query(ContentReview).filter(
            ContentReview.workspace_id == workspace_id,
            ContentReview.id == approval_in.review_id,
        ).first()
        if not review:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target review not found in workspace.")
        return approval_service.request_review_approval(
            db=db,
            review_id=approval_in.review_id,
            user=current_user,
            comment=approval_in.comment,
            reviewer_id=approval_in.reviewer_id,
        )

    if approval_in.brand_rule_id:
        rule = db.query(BrandRule).filter(
            BrandRule.workspace_id == workspace_id,
            BrandRule.id == approval_in.brand_rule_id,
        ).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target rule not found in workspace.")
        return approval_service.request_rule_approval(
            db=db,
            rule_id=approval_in.brand_rule_id,
            user=current_user,
            comment=approval_in.comment,
            reviewer_id=approval_in.reviewer_id,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide either review_id or brand_rule_id.")


# ============================================================================
# APPROVAL DECISION ENDPOINTS
# ============================================================================

@router.get(
    "/approvals/{approval_id:int}",
    response_model=ApprovalOut,
    summary="Get single approval item by ID",
)
def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = approval_service.get_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
    _verify_approval_access(db, approval, current_user, require_decision_role=False)
    return approval


@router.post(
    "/approvals/{approval_id:int}/approve",
    response_model=ApprovalOut,
    summary="Approve a review or brand rule",
)
def approve_request(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = approval_service.get_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
    _verify_approval_access(db, approval, current_user, require_decision_role=True)

    try:
        return approval_service.approve(db=db, approval=approval, reviewer=current_user)
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/approvals/{approval_id:int}/request-changes",
    response_model=ApprovalOut,
    summary="Request changes on a submitted review or rule",
)
def request_changes_on_approval(
    approval_id: int,
    payload: RequestChangesPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = approval_service.get_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
    _verify_approval_access(db, approval, current_user, require_decision_role=True)

    try:
        return approval_service.request_changes(
            db=db,
            approval=approval,
            reviewer=current_user,
            comment=payload.comment,
        )
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/approvals/{approval_id:int}/reject",
    response_model=ApprovalOut,
    summary="Reject a submitted review or rule",
)
def reject_approval(
    approval_id: int,
    payload: RejectApprovalPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    approval = approval_service.get_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
    _verify_approval_access(db, approval, current_user, require_decision_role=True)

    try:
        return approval_service.reject(
            db=db,
            approval=approval,
            reviewer=current_user,
            reason=payload.reason,
        )
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


# PATCH endpoint for backward compatibility with workspace-scoped route
@router.patch(
    "/workspaces/{workspace_id}/approvals/{approval_id}",
    response_model=ApprovalOut,
    summary="Legacy patch approval decision",
)
def patch_approval_legacy(
    workspace_id: int,
    approval_id: int,
    decision_status: str = Query(..., description="Decision: 'approved', 'rejected', or 'changes_requested'"),
    comment: Optional[str] = Query(None, description="Reviewer feedback or notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: int = Depends(verify_workspace_access),
):
    approval = approval_service.get_by_id(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")

    ws_id = approval_service.get_approval_workspace_id(db, approval)
    if ws_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found in this workspace.")

    _verify_approval_access(db, approval, current_user, require_decision_role=True)

    try:
        if decision_status == "approved":
            return approval_service.approve(db=db, approval=approval, reviewer=current_user)
        elif decision_status == "changes_requested":
            return approval_service.request_changes(
                db=db,
                approval=approval,
                reviewer=current_user,
                comment=comment or "Changes requested",
            )
        elif decision_status == "rejected":
            return approval_service.reject(
                db=db,
                approval=approval,
                reviewer=current_user,
                reason=comment or "Rejected by reviewer",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown decision_status: {decision_status}",
            )
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
