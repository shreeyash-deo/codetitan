from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.approval import Approval
from app.models.review import ContentReview
from app.models.rule import BrandRule
from app.models.activity import ReviewActivity
from app.models.user import User
from app.models.version import ContentVersion
from app.models.finding import Finding


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
        db: Session,
        workspace_id: int,
        status: Optional[str] = None,
        submitted_by: Optional[int] = None,
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
        if submitted_by is not None:
            query = query.filter(
                or_(
                    Approval.submitted_by == submitted_by,
                    ContentReview.submitted_by == submitted_by,
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
        query = db.query(ContentReview).filter(ContentReview.id == review_id)
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update()
        review = query.first()
        if not review:
            raise ValueError("Content review not found.")

        if review.status == "approved":
            raise ValueError("Cannot request approval for an already approved review.")

        import hashlib
        current_hash = hashlib.sha256(review.content.strip().encode("utf-8")).hexdigest()

        audit_status = getattr(review, "audit_status", None)
        if audit_status != "verified":
            raise ValueError(
                f"Cannot request approval: Content compliance audit status is '{audit_status}'. "
                f"Please recheck content before requesting sign-off."
            )

        audited_hash = getattr(review, "audited_content_hash", None)
        if not audited_hash or audited_hash != current_hash:
            raise ValueError(
                "Cannot request approval: Current working content does not match a verified audit. "
                "Please recheck content before requesting sign-off."
            )

        # Identify the exact current ContentVersion
        current_ver_num = getattr(review, "current_version_number", 1) or 1
        current_version = (
            db.query(ContentVersion)
            .filter(
                ContentVersion.review_id == review.id,
                ContentVersion.version_number == current_ver_num,
            )
            .first()
        )
        if not current_version:
            raise ValueError(
                f"Cannot request approval: Content version snapshot v{current_ver_num} not found. "
                "Please re-audit content before requesting sign-off."
            )

        if current_version.content_hash != audited_hash:
            raise ValueError(
                "Cannot request approval: Version content hash does not match current audited content. "
                "Please recheck content before requesting sign-off."
            )

        if current_version.audit_status != "verified":
            raise ValueError(
                f"Cannot request approval: Version audit status is '{current_version.audit_status}'. "
                "Audit status must be 'verified' before requesting sign-off."
            )

        clean_comment = comment.strip() if comment and comment.strip() else None

        # If comment contains an automated submission summary, route it to submission_summary
        # so it is recorded as a system activity event and never treated as a human comment
        if clean_comment and is_automated_submission_summary(clean_comment):
            if not submission_summary:
                submission_summary = clean_comment
            clean_comment = None

        # Check for existing pending approval tickets
        existing_pending = (
            db.query(Approval)
            .filter(Approval.review_id == review.id, Approval.status == "pending")
            .all()
        )

        same_version_ticket = None
        for pending_ticket in existing_pending:
            if (
                pending_ticket.version_id == current_version.id
                and pending_ticket.version_number == current_ver_num
                and pending_ticket.content_hash == current_version.content_hash
            ):
                if same_version_ticket is None:
                    same_version_ticket = pending_ticket
                else:
                    pending_ticket.status = "superseded"
                    pending_ticket.updated_at = datetime.now(timezone.utc)
            else:
                # Ticket belongs to an older/different version or content hash.
                # DO NOT modify its version_id, version_number, or content_hash.
                # Preserve its historical binding, submitter, reviewer, and comment.
                pending_ticket.status = "superseded"
                pending_ticket.updated_at = datetime.now(timezone.utc)

        if same_version_ticket:
            approval = same_version_ticket
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
                version_id=current_version.id,
                version_number=current_ver_num,
                content_hash=current_version.content_hash,
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

        is_auto_event = is_automated_submission_summary(activity_details)

        if should_record_activity:
            activity = ReviewActivity(
                review_id=review.id,
                workspace_id=review.workspace_id,
                user_id=None if is_auto_event else user.id,
                action="Approval requested",
                details=activity_details,
            )
            db.add(activity)
        elif submission_summary and latest_activity:
            latest_activity.details = submission_summary
            if is_auto_event:
                latest_activity.user_id = None

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

        if approval.status != "pending":
            raise ValueError(f"Approval ticket has status '{approval.status}' and cannot be approved.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if not review:
                raise ValueError("Content review not found.")

            if review.status == "approved":
                raise ValueError("Content review has already been approved.")

            # 1. Verify approval ticket is bound to an immutable version snapshot
            if not approval.version_id:
                raise ValueError("Cannot approve ticket: Approval ticket is not bound to a verified version snapshot.")

            target_version = db.query(ContentVersion).filter(ContentVersion.id == approval.version_id).first()
            if not target_version:
                raise ValueError("Cannot approve ticket: Bound content version snapshot does not exist.")

            # 2. Version number must match that version
            if approval.version_number is not None and approval.version_number != target_version.version_number:
                raise ValueError(
                    f"Cannot approve ticket: Version number mismatch (ticket: v{approval.version_number}, snapshot: v{target_version.version_number})."
                )

            # 3. Content hash must match immutable version hash
            if not approval.content_hash or approval.content_hash != target_version.content_hash:
                raise ValueError("Cannot approve ticket: Approval ticket content hash does not match version snapshot hash.")

            # 4. Version must still be the current review version
            current_ver_num = getattr(review, "current_version_number", 1) or 1
            if target_version.version_number != current_ver_num:
                raise ValueError(
                    f"Cannot approve stale ticket: Ticket is for version v{target_version.version_number}, but current content is v{current_ver_num}."
                )

            # 5. Current review's audited_content_hash matches approval's content_hash
            if not review.audited_content_hash or review.audited_content_hash != approval.content_hash:
                raise ValueError("Cannot approve ticket: Review audited content hash does not match approved ticket hash.")

            # 6. Compliance audit status must be verified
            if getattr(review, "audit_status", None) != "verified" or target_version.audit_status != "verified":
                raise ValueError(
                    f"Cannot approve ticket: Compliance audit status must be 'verified' (review: '{review.audit_status}', version: '{target_version.audit_status}')."
                )

            # 7. No unresolved critical findings exist for the version being approved
            open_critical_findings = (
                db.query(Finding)
                .filter(
                    Finding.review_id == review.id,
                    or_(
                        Finding.version_id == target_version.id,
                        Finding.version_id.is_(None),
                    ),
                    Finding.severity == "critical",
                    Finding.status == "open",
                )
                .all()
            )
            if open_critical_findings:
                raise ValueError(
                    f"Cannot approve review with {len(open_critical_findings)} open critical compliance violation(s). "
                    "All critical findings must be corrected or resolved before sign-off."
                )

            # Atomic conditional update of review status
            rows = db.query(ContentReview).filter(
                ContentReview.id == approval.review_id,
                ContentReview.status != "approved"
            ).update({"status": "approved"}, synchronize_session=False)

            if rows == 0:
                raise ValueError("Content review has already been approved.")

            # Update ONLY this intended approval ticket (no destructive bulk updates!)
            approval.status = "approved"
            approval.reviewer_id = reviewer.id
            approval.updated_at = datetime.now(timezone.utc)

            # Prevent duplicate "Review approved" activity
            existing_act = db.query(ReviewActivity).filter(
                ReviewActivity.review_id == approval.review_id,
                ReviewActivity.action == "Review approved",
                ReviewActivity.details.like(f"%v{target_version.version_number}%")
            ).first()

            if not existing_act:
                activity = ReviewActivity(
                    review_id=approval.review_id,
                    workspace_id=review.workspace_id if review else ws_id,
                    user_id=reviewer.id,
                    action="Review approved",
                    details=f"Approved by {reviewer.name} (v{target_version.version_number}).",
                )
                db.add(activity)

        elif approval.brand_rule_id:
            rule = db.query(BrandRule).filter(BrandRule.id == approval.brand_rule_id).first()
            if not rule:
                raise ValueError("Brand rule not found.")
            if rule.approval_status == "approved":
                raise ValueError("Brand rule has already been approved.")

            rule_rows = db.query(BrandRule).filter(
                BrandRule.id == approval.brand_rule_id,
                BrandRule.approval_status != "approved"
            ).update({"approval_status": "approved"}, synchronize_session=False)

            if rule_rows == 0:
                raise ValueError("Brand rule has already been approved.")

            approval.status = "approved"
            approval.reviewer_id = reviewer.id
            approval.updated_at = datetime.now(timezone.utc)

            rule_title = rule.title if rule else f"Rule {approval.brand_rule_id}"
            activity = ReviewActivity(
                review_id=None,
                workspace_id=ws_id,
                user_id=reviewer.id,
                action="Brand rule approved",
                details=f"Rule '{rule_title}' approved as official brand knowledge by {reviewer.name}.",
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

        clean_comment = comment.strip()

        if approval.status == "approved":
            raise ValueError("Cannot request changes on an already approved item.")

        if approval.status != "pending":
            raise ValueError(f"Cannot request changes on a ticket with status '{approval.status}'.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if not review:
                raise ValueError("Content review not found.")
            if review.status == "approved":
                raise ValueError("Cannot request changes on an already approved review.")

            review.status = "needs_revision"

            # Update ONLY the intended pending ticket
            approval.status = "changes_requested"
            approval.comment = clean_comment
            approval.reviewer_id = reviewer.id
            approval.updated_at = datetime.now(timezone.utc)

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
            approval.updated_at = datetime.now(timezone.utc)

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

        if approval.status != "pending":
            raise ValueError(f"Cannot reject a ticket with status '{approval.status}'.")

        if approval.review_id:
            review = db.query(ContentReview).filter(ContentReview.id == approval.review_id).first()
            if not review:
                raise ValueError("Content review not found.")
            if review.status == "approved":
                raise ValueError("Cannot reject an already approved review.")

            review.status = "rejected"

            # Update ONLY the intended pending ticket
            approval.status = "rejected"
            approval.comment = clean_reason
            approval.reviewer_id = reviewer.id
            approval.updated_at = datetime.now(timezone.utc)

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
            if not rule:
                raise ValueError("Brand rule not found.")
            if rule.approval_status == "approved":
                raise ValueError("Cannot reject an already approved brand rule.")

            rule.approval_status = "rejected"
            approval.status = "rejected"
            approval.comment = clean_reason
            approval.reviewer_id = reviewer.id
            approval.updated_at = datetime.now(timezone.utc)

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
