from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.approval import Approval
from app.models.review import ContentReview
from app.models.rule import BrandRule
from app.models.activity import ReviewActivity
from app.models.user import User


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
    ) -> Approval:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Content review not found.")

        # Create or update pending approval request
        approval = Approval(
            review_id=review.id,
            brand_rule_id=None,
            submitted_by=user.id,
            reviewer_id=reviewer_id,
            status="pending",
            comment=comment,
        )
        db.add(approval)

        activity = ReviewActivity(
            review_id=review.id,
            workspace_id=review.workspace_id,
            user_id=user.id,
            action="Approval requested",
            details=comment or f"Submitted by {user.name} for human reviewer sign-off.",
        )
        db.add(activity)

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

        approval.status = "approved"
        approval.reviewer_id = reviewer.id

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review:
                review.status = "approved"
                activity = ReviewActivity(
                    review_id=review.id,
                    workspace_id=review.workspace_id,
                    user_id=reviewer.id,
                    action="Review approved",
                    details=f"Approved by {reviewer.name}.",
                )
                db.add(activity)

        if approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if rule:
                rule.approval_status = "approved"
                activity = ReviewActivity(
                    review_id=None,
                    workspace_id=rule.workspace_id,
                    user_id=reviewer.id,
                    action="Brand rule approved",
                    details=f"Rule '{rule.title}' approved as official brand knowledge by {reviewer.name}.",
                )
                db.add(activity)

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

        if approval.status == "approved":
            raise ValueError("Cannot request changes on an already approved item.")

        approval.status = "changes_requested"
        approval.comment = comment.strip()
        approval.reviewer_id = reviewer.id

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review:
                review.status = "needs_revision"
                activity = ReviewActivity(
                    review_id=review.id,
                    workspace_id=review.workspace_id,
                    user_id=reviewer.id,
                    action="Changes requested",
                    details=comment.strip(),
                )
                db.add(activity)

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

        approval.status = "rejected"
        approval.comment = reason.strip()
        approval.reviewer_id = reviewer.id

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if review:
                review.status = "rejected"
                activity = ReviewActivity(
                    review_id=review.id,
                    workspace_id=review.workspace_id,
                    user_id=reviewer.id,
                    action="Review rejected",
                    details=reason.strip(),
                )
                db.add(activity)

        if approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if rule:
                rule.approval_status = "rejected"
                activity = ReviewActivity(
                    review_id=None,
                    workspace_id=rule.workspace_id,
                    user_id=reviewer.id,
                    action="Brand rule rejected",
                    details=reason.strip(),
                )
                db.add(activity)

        db.commit()
        db.refresh(approval)
        return approval


approval_service = ApprovalService()
