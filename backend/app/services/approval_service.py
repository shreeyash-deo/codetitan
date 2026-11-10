from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.approval import Approval
from app.models.review import ContentReview
from app.models.rule import BrandRule
from app.models.activity import ReviewActivity
from app.models.user import User


def is_automated_submission_summary(text: Optional[str]) -> bool:
    if not text:
        return False
    lower = text.strip().lower()
    return (
        lower.startswith("submitted for sign-off with")
        or lower.startswith("submitted for tier")
        or lower.startswith("submitted by")
        or lower.startswith("submission summary:")
        or "corrections applied. current compliance score:" in lower
    )


class ApprovalService:
    @staticmethod
    def get_by_id(db: Session, approval_id: int) -> Optional[Approval]:
        return db.query(Approval).filter(Approval.id == approval_id).first()

    @staticmethod
    def get_approval_workspace_id(db: Session, approval: Approval) -> Optional[int]:
        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review:
                return review.workspace_id
        if approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if rule:
                return rule.workspace_id
        return None

    @staticmethod
    def list_workspace_approvals(
        db: Session, workspace_id: int, status: Optional[str] = None
    ) -> List[Approval]:
        query = (
            db.query(Approval)
            .outerjoin(ContentReview, Approval.review_id == ContentReview.id)
            .outerjoin(BrandRule, Approval.brand_rule_id == BrandRule.id)
            .filter(
                or_(
                    ContentReview.workspace_id == workspace_id,
                    BrandRule.workspace_id == workspace_id,
                )
            )
        )
        if status:
            query = query.filter(Approval.status == status.lower())
        return query.order_by(Approval.created_at.desc()).all()

    @staticmethod
    def request_review_approval(
        db: Session,
        review_id: int,
        user: User,
        comment: Optional[str] = None,
        reviewer_id: Optional[int] = None,
        submission_summary: Optional[str] = None,
    ) -> Approval:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Content review not found.")

        if review.status == "approved":
            raise ValueError("Cannot request approval for an already approved review.")

        clean_comment = comment.strip() if comment and comment.strip() else None

        # If comment contains an automated submission summary, route it to submission_summary
        # so it is recorded as a system activity event and never treated as a human comment
        if clean_comment and is_automated_submission_summary(clean_comment):
            if not submission_summary:
                submission_summary = clean_comment
            clean_comment = None

        # Check for existing pending approval request to prevent duplicate approval requests
        existing_approval = (
            db.query(Approval)
            .filter(Approval.review_id == review.id, Approval.status == "pending")
            .first()
        )
        if existing_approval:
            approval = existing_approval
            if clean_comment:
                approval.comment = clean_comment
            if reviewer_id:
                approval.reviewer_id = reviewer_id
        else:
            approval = Approval(
                review_id=review.id,
                brand_rule_id=None,
                submitted_by=user.id,
                reviewer_id=reviewer_id,
                status="pending",
                comment=clean_comment,
            )
            db.add(approval)

        review.status = "pending"

        # Check latest activity to prevent duplicate entries on retry/double-click
        latest_activity = (
            db.query(ReviewActivity)
            .filter(ReviewActivity.review_id == review.id)
            .order_by(ReviewActivity.created_at.desc(), ReviewActivity.id.desc())
            .first()
        )
        should_record_activity = (not latest_activity or latest_activity.action != "Approval requested")

        activity_details = (
            submission_summary
            or (clean_comment if not is_automated_submission_summary(clean_comment) else None)
            or f"Submitted by {user.name} for human reviewer sign-off."
        )

        if should_record_activity:
            activity = ReviewActivity(
                review_id=review.id,
                workspace_id=review.workspace_id,
                user_id=user.id,
                action="Approval requested",
                details=activity_details,
            )
            db.add(activity)
        elif submission_summary and latest_activity:
            latest_activity.details = submission_summary

        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def request_rule_approval(
        db: Session,
        rule_id: int,
        user: User,
        comment: Optional[str] = None,
        reviewer_id: Optional[int] = None,
    ) -> Approval:
        rule = db.query(BrandRule).filter(BrandRule.id == rule_id).first()
        if not rule:
            raise ValueError("Brand rule not found.")

        approval = Approval(
            review_id=None,
            brand_rule_id=rule.id,
            submitted_by=user.id,
            reviewer_id=reviewer_id,
            status="pending",
            comment=comment,
        )
        db.add(approval)

        activity = ReviewActivity(
            review_id=None,
            workspace_id=rule.workspace_id,
            user_id=user.id,
            action="Brand rule approval requested",
            details=comment or f"Rule '{rule.title}' submitted by {user.name} for approval.",
        )
        db.add(activity)

        db.commit()
        db.refresh(approval)
        return approval

    @classmethod
    def verify_reviewer_permission(cls, user: User, workspace_id: int, db: Session) -> None:
        """Ensure the user is authorized in this workspace as an Admin or Reviewer."""
        from app.models.workspace_member import WorkspaceMember
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.status == "approved",
            )
            .first()
        )
        if not membership or membership.role.lower() not in ("admin", "reviewer"):
            raise PermissionError("Only authorized reviewers or workspace admins can decide approvals.")

    @classmethod
    def verify_workspace_role_for_approval(
        cls, user: User, workspace_id: int, required_roles: tuple, db: Session
    ) -> None:
        """Ensure the user is authorized in this workspace with one of required_roles."""
        from app.models.workspace_member import WorkspaceMember
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.status == "approved",
            )
            .first()
        )
        if not membership or membership.role.lower() not in [r.lower() for r in required_roles]:
            role_names = " or ".join(required_roles)
            raise PermissionError(f"Only workspace {role_names} can decide this approval.")

    @classmethod
    def approve(cls, db: Session, approval: Approval, reviewer: User) -> Approval:
        ws_id = cls.get_approval_workspace_id(db, approval)
        if ws_id is not None:
            if approval.brand_rule_id:
                # Authoritative brand rule approvals strictly require workspace Admin
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin",), db)
            else:
                # Content review sign-off allows Reviewer or Admin
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin", "Reviewer"), db)

        if approval.status == "approved":
            raise ValueError("Item has already been approved.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review and review.status == "approved":
                approval.status = "approved"
                approval.reviewer_id = reviewer.id
                db.commit()
                raise ValueError("Content review has already been approved.")

            # Atomic conditional update
            rows = db.query(ContentReview).filter(
                ContentReview.id == approval.review_id,
                ContentReview.status != "approved"
            ).update({"status": "approved"}, synchronize_session=False)

            if rows == 0:
                approval.status = "approved"
                approval.reviewer_id = reviewer.id
                db.commit()
                raise ValueError("Content review has already been approved.")

            # Update all approvals for this review
            db.query(Approval).filter(
                Approval.review_id == approval.review_id
            ).update(
                {"status": "approved", "reviewer_id": reviewer.id},
                synchronize_session=False
            )

            # Prevent duplicate "Review approved" activity
            existing_act = db.query(ReviewActivity).filter(
                ReviewActivity.review_id == approval.review_id,
                ReviewActivity.action == "Review approved"
            ).first()

            if not existing_act:
                activity = ReviewActivity(
                    review_id=approval.review_id,
                    workspace_id=review.workspace_id if review else ws_id,
                    user_id=reviewer.id,
                    action="Review approved",
                    details=f"Approved by {reviewer.name}.",
                )
                db.add(activity)

        elif approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if rule and rule.approval_status == "approved":
                approval.status = "approved"
                approval.reviewer_id = reviewer.id
                db.commit()
                raise ValueError("Brand rule has already been approved.")

            rule_rows = db.query(BrandRule).filter(
                BrandRule.id == approval.brand_rule_id,
                BrandRule.approval_status != "approved"
            ).update({"approval_status": "approved"}, synchronize_session=False)

            if rule_rows == 0:
                approval.status = "approved"
                approval.reviewer_id = reviewer.id
                db.commit()
                raise ValueError("Brand rule has already been approved.")

            existing_act = db.query(ReviewActivity).filter(
                ReviewActivity.workspace_id == ws_id,
                ReviewActivity.action == "Brand rule approved",
                ReviewActivity.details.like(f"%'{rule.title}' approved%") if rule else ReviewActivity.details.like(f"%Rule {approval.brand_rule_id}%")
            ).first()

            if not existing_act:
                rule_title = rule.title if rule else f"Rule {approval.brand_rule_id}"
                activity = ReviewActivity(
                    review_id=None,
                    workspace_id=ws_id,
                    user_id=reviewer.id,
                    action="Brand rule approved",
                    details=f"Rule '{rule_title}' approved as official brand knowledge by {reviewer.name}.",
                )
                db.add(activity)

        approval.status = "approved"
        approval.reviewer_id = reviewer.id
        db.commit()
        db.refresh(approval)
        return approval

    @classmethod
    def request_changes(
        cls, db: Session, approval: Approval, reviewer: User, comment: str
    ) -> Approval:
        ws_id = cls.get_approval_workspace_id(db, approval)
        if ws_id is not None:
            if approval.brand_rule_id:
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin",), db)
            else:
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin", "Reviewer"), db)

        if not comment or not comment.strip():
            raise ValueError("Requesting changes requires specific feedback instructions.")

        clean_comment = comment.strip()

        if approval.status == "approved":
            raise ValueError("Cannot request changes on an already approved item.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review and review.status == "approved":
                raise ValueError("Cannot request changes on an already approved review.")

            is_already_revision = (review.status == "needs_revision") if review else False
            if review:
                review.status = "needs_revision"

            approval.status = "changes_requested"
            approval.comment = clean_comment
            approval.reviewer_id = reviewer.id

            if not is_already_revision:
                activity = ReviewActivity(
                    review_id=review.id,
                    workspace_id=review.workspace_id,
                    user_id=reviewer.id,
                    action="Changes requested",
                    details=clean_comment,
                )
                db.add(activity)

        elif approval.brand_rule_id:
            approval.status = "changes_requested"
            approval.comment = clean_comment
            approval.reviewer_id = reviewer.id

        db.commit()
        db.refresh(approval)
        return approval

    @classmethod
    def reject(
        cls, db: Session, approval: Approval, reviewer: User, reason: str
    ) -> Approval:
        ws_id = cls.get_approval_workspace_id(db, approval)
        if ws_id is not None:
            if approval.brand_rule_id:
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin",), db)
            else:
                cls.verify_workspace_role_for_approval(reviewer, ws_id, ("Admin", "Reviewer"), db)

        if not reason or not reason.strip():
            raise ValueError("Rejection requires a documented reason.")

        clean_reason = reason.strip()

        if approval.status == "approved":
            raise ValueError("Cannot reject an already approved item.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review and review.status == "approved":
                raise ValueError("Cannot reject an already approved review.")

            is_already_rejected = (review.status == "rejected") if review else False
            if review:
                review.status = "rejected"

            approval.status = "rejected"
            approval.comment = clean_reason
            approval.reviewer_id = reviewer.id

            if not is_already_rejected:
                activity = ReviewActivity(
                    review_id=review.id,
                    workspace_id=review.workspace_id,
                    user_id=reviewer.id,
                    action="Review rejected",
                    details=clean_reason,
                )
                db.add(activity)

        elif approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if rule and rule.approval_status == "approved":
                raise ValueError("Cannot reject an already approved brand rule.")

            is_already_rejected = (rule.approval_status == "rejected") if rule else False
            if rule:
                rule.approval_status = "rejected"

            approval.status = "rejected"
            approval.comment = clean_reason
            approval.reviewer_id = reviewer.id

            if not is_already_rejected:
                activity = ReviewActivity(
                    review_id=None,
                    workspace_id=ws_id,
                    user_id=reviewer.id,
                    action="Brand rule rejected",
                    details=clean_reason,
                )
                db.add(activity)

        db.commit()
        db.refresh(approval)
        return approval


approval_service = ApprovalService()
