from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import (
    verify_workspace_access,
    get_current_user,
    get_workspace_member,
    require_workspace_admin,
)
from app.models.rule import BrandRule
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.rule import BrandRuleCreate, BrandRuleUpdate, BrandRuleOut
from app.services.rule_service import rule_service
from app.services.workspace_service import workspace_service

router = APIRouter(tags=["Brand Rules"])


def get_rule_with_access(
    rule_id: int,
    db: Session,
    current_user: User,
) -> BrandRule:
    """Helper to retrieve a brand rule and verify the user has access to its workspace."""
    rule = rule_service.get_by_id(db, rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand rule not found.",
        )

    if not workspace_service.is_member(db, rule.workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the workspace containing this rule.",
        )
    return rule


def verify_rule_admin_access(rule: BrandRule, user_id: int, db: Session):
    member = workspace_service.get_member(db, rule.workspace_id, user_id)
    if not member or member.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Required workspace role: Admin",
        )


@router.get(
    "/workspaces/{workspace_id}/rules",
    response_model=List[BrandRuleOut],
    summary="List brand rules in a workspace",
)
def list_rules(
    workspace_id: int,
    approval_status: Optional[str] = Query(None, description="Filter by approval status (approved, pending, rejected)"),
    status: Optional[str] = Query(None, description="Alias for approval_status filter"),
    category: Optional[str] = Query(None, description="Filter by rule category"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_workspace_member),
):
    """
    List brand rules for a workspace.
    Employees can view approved rules only.
    Admins and Reviewers can query rules across all approval statuses.
    """
    eff_status = approval_status or status
    if member.role.lower() in ("employee", "editor"):
        # Strict boundary: Employees can only view approved authoritative brand rules
        eff_status = "approved"

    return rule_service.list_rules(
        db=db,
        workspace_id=workspace_id,
        approval_status=eff_status,
        category=category,
    )


@router.get(
    "/workspaces/{workspace_id}/rules/pending",
    response_model=List[BrandRuleOut],
    summary="List pending candidate rules awaiting human review",
)
def list_pending_rules(
    workspace_id: int,
    category: Optional[str] = Query(None, description="Filter by rule category"),
    db: Session = Depends(get_db),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    """Retrieve all pending AI-extracted rules waiting for human approval (Admin only)."""
    return rule_service.list_rules(
        db=db,
        workspace_id=workspace_id,
        approval_status="pending",
        category=category,
    )


@router.post(
    "/workspaces/{workspace_id}/rules",
    response_model=BrandRuleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a brand rule",
)
def create_manual_rule(
    workspace_id: int,
    rule_in: BrandRuleCreate,
    db: Session = Depends(get_db),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    """Create a new official or pending brand rule manually (Admin only)."""
    rule = BrandRule(
        workspace_id=workspace_id,
        document_id=rule_in.document_id,
        title=rule_in.title.strip(),
        description=rule_in.description.strip(),
        category=rule_in.category.strip(),
        source_reference=rule_in.source_reference,
        confidence=rule_in.confidence,
        approval_status=rule_in.approval_status or "pending",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get(
    "/rules/{rule_id}",
    response_model=BrandRuleOut,
    summary="Get brand rule by ID",
)
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a specific brand rule."""
    return get_rule_with_access(rule_id, db, current_user)


@router.patch(
    "/rules/{rule_id}",
    response_model=BrandRuleOut,
    summary="Edit a candidate or existing brand rule",
)
@router.patch(
    "/workspaces/{workspace_id}/rules/{rule_id}",
    response_model=BrandRuleOut,
    summary="Edit a brand rule (workspace-scoped route)",
    include_in_schema=False,
)
def update_rule(
    rule_id: int,
    rule_in: BrandRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update title, description, category, or citations on a rule (Admin only)."""
    rule = get_rule_with_access(rule_id, db, current_user)
    verify_rule_admin_access(rule, current_user.id, db)
    return rule_service.update_rule(db, rule, rule_in)


@router.post(
    "/rules/{rule_id}/approve",
    response_model=BrandRuleOut,
    summary="Approve a candidate rule as official brand knowledge",
)
def approve_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Authorized human governance action: Mark rule as approved (Admin only).
    Only Admins can approve authoritative brand rules.
    """
    rule = get_rule_with_access(rule_id, db, current_user)
    verify_rule_admin_access(rule, current_user.id, db)
    return rule_service.approve_rule(db, rule, reviewer_id=current_user.id)


@router.post(
    "/rules/{rule_id}/reject",
    response_model=BrandRuleOut,
    summary="Reject a candidate brand rule",
)
def reject_rule(
    rule_id: int,
    reason: Optional[str] = Query(None, description="Optional rejection rationale"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark candidate rule as rejected (Admin only).
    """
    rule = get_rule_with_access(rule_id, db, current_user)
    verify_rule_admin_access(rule, current_user.id, db)
    return rule_service.reject_rule(db, rule, reviewer_id=current_user.id, reason=reason)


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a brand rule",
)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a brand rule (Admin only)."""
    rule = get_rule_with_access(rule_id, db, current_user)
    verify_rule_admin_access(rule, current_user.id, db)
    db.delete(rule)
    db.commit()
    return None
