from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import verify_workspace_access, get_current_user, get_workspace_member
from app.models.review import ContentReview
from app.models.activity import ReviewActivity
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.review import (
    ContentReviewSubmission,
    ContentReviewUpdate,
    ContentReviewOut,
    PaginatedReviewsOut,
    ApplyCorrectionResponse,
)
from app.schemas.finding import FindingOut
from app.schemas.approval import ApprovalOut, RequestApprovalPayload
from app.schemas.activity import ReviewActivityOut
from app.services.review_service import review_service
from app.services.approval_service import approval_service
from app.services.workspace_service import workspace_service
from app.services.compliance.compliance_engine import NoApprovedRulesError

router = APIRouter(tags=["Content Reviews & Compliance"])


def get_review_with_access(
    review_id: int,
    db: Session,
    current_user: User,
) -> ContentReview:
    """Helper to retrieve content review and verify workspace access."""
    review = review_service.get_by_id(db, review_id=review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content review not found.",
        )

    member = workspace_service.get_member(db, review.workspace_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the workspace containing this review.",
        )

    if member.role.lower() in ("employee", "editor") and review.submitted_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Employees may only view their own submitted reviews.",
        )
    return review


@router.post(
    "/workspaces/{workspace_id}/reviews",
    response_model=ContentReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit marketing content and run automated compliance engine",
)
def submit_and_review_content(
    workspace_id: int,
    submission: ContentReviewSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: int = Depends(verify_workspace_access),
):
    """
    Submit marketing copy for automated compliance review against approved brand rules.
    Runs hybrid checks (Python deterministic + AI contextual) and computes the compliance score.
    """
    if not submission.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submitted content cannot be empty.",
        )

    try:
        review = review_service.submit_and_audit(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            submission=submission,
        )
        return review
    except NoApprovedRulesError as rule_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(rule_err),
        )
    except TimeoutError as timeout_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"AI analysis timed out: {timeout_err}",
        )
    except (RuntimeError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Compliance provider error: {err}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error running compliance engine: {exc}",
        )


@router.get(
    "/workspaces/{workspace_id}/reviews",
    response_model=PaginatedReviewsOut,
    summary="List content reviews for a workspace with search, filter, sort and pagination",
)
def list_reviews(
    workspace_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search review title"),
    status: Optional[str] = Query(None, description="Filter by status (compliant, needs_changes, critical_issues, approved, etc.)"),
    content_type: Optional[str] = Query(None, description="Filter by content_type (social_media, blog, email, website, advertisement, other)"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    sort_by: str = Query("created_at", description="Sort by 'created_at' or 'compliance_score'"),
    sort_order: str = Query("desc", description="Sort order 'asc' or 'desc'"),
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
):
    """List historical content reviews in the workspace with pagination, full-text search, and status filters."""
    submitted_by = current_user.id if member.role.lower() in ("employee", "editor") else None
    return review_service.list_reviews(
        db=db,
        workspace_id=workspace_id,
        page=page,
        size=size,
        search=search,
        status=status,
        content_type=content_type,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        submitted_by=submitted_by,
    )


@router.get(
    "/reviews/{review_id}",
    response_model=ContentReviewOut,
    summary="Get content review details by ID",
)
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full compliance report, findings, original/corrected content, and timeline activities."""
    return get_review_with_access(review_id, db, current_user)


@router.get(
    "/workspaces/{workspace_id}/reviews/{review_id}",
    response_model=ContentReviewOut,
    summary="Get content review details by workspace ID and review ID (alias)",
)
def get_workspace_review(
    workspace_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: int = Depends(verify_workspace_access),
):
    """Retrieve review details scoped to workspace."""
    review = get_review_with_access(review_id, db, current_user)
    if review.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content review does not belong to this workspace.",
        )
    return review


@router.patch(
    "/reviews/{review_id}",
    response_model=ContentReviewOut,
    summary="Update review metadata or content",
)
def update_review(
    review_id: int,
    review_in: ContentReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update title, working content, or review status. If content changed, re-audits atomically."""
    review = get_review_with_access(review_id, db, current_user)
    update_data = review_in.model_dump(exclude_unset=True)

    content_changed = "content" in update_data and update_data["content"] != review.content
    new_content = update_data.pop("content", None)

    for field, value in update_data.items():
        setattr(review, field, value)

    if content_changed and new_content is not None:
        review = review_service.recheck_and_audit(
            db=db,
            review_id=review.id,
            new_content=new_content,
            user_id=current_user.id,
        )
    else:
        db.commit()
        db.refresh(review)

    return review


@router.post(
    "/reviews/{review_id}/findings/batch-apply",
    response_model=ContentReviewOut,
    summary="Batch apply all pending suggestions and re-audit working document",
)
def batch_apply_findings(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_review_with_access(review_id, db, current_user)
    try:
        return review_service.batch_apply_corrections(db, review_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.post(
    "/reviews/{review_id}/recheck",
    response_model=ContentReviewOut,
    summary="Re-audit working content of review against approved brand rules",
)
def recheck_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_review_with_access(review_id, db, current_user)
    try:
        return review_service.recheck_and_audit(db, review_id, user_id=current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a content review",
)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a review and its findings."""
    review = get_review_with_access(review_id, db, current_user)
    db.delete(review)
    db.commit()
    return None


@router.get(
    "/reviews/{review_id}/activity",
    response_model=List[ReviewActivityOut],
    summary="Get activity timeline for a review",
)
def get_review_activity_timeline(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full chronological audit trail and history for this review."""
    get_review_with_access(review_id, db, current_user)
    activities = (
        db.query(ReviewActivity)
        .filter(ReviewActivity.review_id == review_id)
        .order_by(ReviewActivity.created_at.asc())
        .all()
    )
    return activities


# ============================================================================
# CORRECTION FUNCTIONALITY ENDPOINTS
# ============================================================================

@router.post(
    "/reviews/{review_id}/findings/{finding_id}/accept",
    response_model=FindingOut,
    summary="Accept a suggested AI correction",
)
def accept_finding(
    review_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a suggested correction finding as accepted by reviewer."""
    get_review_with_access(review_id, db, current_user)
    try:
        return review_service.accept_finding(db, review_id, finding_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/reject",
    response_model=FindingOut,
    summary="Reject or dismiss a suggested correction",
)
def reject_finding(
    review_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a suggested correction. Recalculates the review compliance score."""
    get_review_with_access(review_id, db, current_user)
    try:
        finding, _ = review_service.reject_finding(db, review_id, finding_id, current_user.id)
        return finding
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/apply",
    response_model=ApplyCorrectionResponse,
    summary="Apply a suggested correction directly to working review content",
)
def apply_correction(
    review_id: int,
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Apply proposed correction to the review's working content.
    Preserves original_content untouched, recalculates compliance score,
    and updates finding status to 'applied'.
    """
    get_review_with_access(review_id, db, current_user)
    try:
        return review_service.apply_correction(db, review_id, finding_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
