import math
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.activity import ReviewActivity
from app.models.rule import BrandRule
from app.schemas.review import (
    ContentReviewSubmission,
    ContentReviewUpdate,
    PaginatedReviewsOut,
    ApplyCorrectionResponse,
)
from app.services.compliance.compliance_engine import compliance_engine, NoApprovedRulesError
from app.services.compliance.scoring_service import scoring_service


class ReviewService:
    @staticmethod
    def get_by_id(db: Session, review_id: int) -> Optional[ContentReview]:
        return db.query(ContentReview).filter(ContentReview.id == review_id).first()

    @staticmethod
    def submit_and_audit(
        db: Session,
        workspace_id: int,
        user_id: Optional[int],
        submission: ContentReviewSubmission,
    ) -> ContentReview:
        """
        1. Fetch all approved rules for the workspace.
        2. Raise NoApprovedRulesError if no approved rules exist.
        3. Execute the hybrid compliance engine (deterministic + AI).
        4. Save review, findings, and activity log.
        """
        # Fetch approved rules only
        approved_rules = (
            db.query(BrandRule)
            .filter(
                BrandRule.workspace_id == workspace_id,
                BrandRule.approval_status == "approved",
            )
            .all()
        )

        if not approved_rules:
            raise NoApprovedRulesError(
                "No approved brand rules found for this workspace. "
                "Brand-specific compliance analysis cannot be completed. "
                "Please approve at least one brand rule in Brand Guidelines first."
            )

        # Run hybrid audit engine
        audit_result = compliance_engine.run_compliance_audit(
            content=submission.content,
            content_type=submission.content_type,
            approved_rules=approved_rules,
        )

        # Persist ContentReview
        review = ContentReview(
            workspace_id=workspace_id,
            title=submission.title.strip(),
            content=submission.content,
            original_content=submission.content,  # Preserve immutable original
            content_type=submission.content_type,
            status=audit_result.status,
            compliance_score=audit_result.compliance_score,
            summary=audit_result.summary,
            submitted_by=user_id,
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        # Persist Findings
        for f in audit_result.findings:
            finding = Finding(
                review_id=review.id,
                severity=f.severity,
                category=f.category,
                excerpt=f.excerpt,
                explanation=f.explanation,
                guideline_reference=f.guideline_reference,
                suggested_correction=f.suggested_correction,
                confidence=f.confidence,
                status="open",
            )
            db.add(finding)

        # Log Activity
        activity = ReviewActivity(
            review_id=review.id,
            user_id=user_id,
            action="Audit Completed",
            details=f"Compliance scan completed. Score: {review.compliance_score}/100. Status: {review.status}.",
        )
        db.add(activity)

        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_reviews(
        db: Session,
        workspace_id: int,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedReviewsOut:
        query = db.query(ContentReview).filter(ContentReview.workspace_id == workspace_id)

        # Title Search
        if search and search.strip():
            query = query.filter(ContentReview.title.ilike(f"%{search.strip()}%"))

        # Status & Content Type Filters
        if status:
            query = query.filter(ContentReview.status == status.lower())
        if content_type:
            query = query.filter(ContentReview.content_type == content_type.lower())

        # Date Range Filter
        if start_date:
            query = query.filter(ContentReview.created_at >= start_date)
        if end_date:
            query = query.filter(ContentReview.created_at <= end_date)

        total = query.count()
        pages = math.ceil(total / size) if size > 0 else 1
        offset = (page - 1) * size

        # Sorting
        sort_col = ContentReview.compliance_score if sort_by == "compliance_score" else ContentReview.created_at
        if sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        items = query.offset(offset).limit(size).all()

        return PaginatedReviewsOut(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    @staticmethod
    def accept_finding(db: Session, review_id: int, finding_id: int, user_id: Optional[int]) -> Finding:
        finding = (
            db.query(Finding)
            .filter(Finding.id == finding_id, Finding.review_id == review_id)
            .first()
        )
        if not finding:
            raise ValueError("Finding not found for this review.")

        finding.status = "accepted"
        activity = ReviewActivity(
            review_id=review_id,
            user_id=user_id,
            action="Suggestion Accepted",
            details=f"Accepted suggestion for '{finding.excerpt}'.",
        )
        db.add(activity)
        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def reject_finding(db: Session, review_id: int, finding_id: int, user_id: Optional[int]) -> Tuple[Finding, ContentReview]:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found.")

        finding = (
            db.query(Finding)
            .filter(Finding.id == finding_id, Finding.review_id == review_id)
            .first()
        )
        if not finding:
            raise ValueError("Finding not found for this review.")

        finding.status = "rejected"

        # Recalculate score without rejected finding
        all_findings = db.query(Finding).filter(Finding.review_id == review_id).all()
        new_score, new_status = scoring_service.calculate_score(all_findings)
        review.compliance_score = new_score
        review.status = new_status

        activity = ReviewActivity(
            review_id=review_id,
            user_id=user_id,
            action="Suggestion Dismissed",
            details=f"Dismissed suggestion for '{finding.excerpt}'. Score updated to {new_score}.",
        )
        db.add(activity)
        db.commit()
        db.refresh(finding)
        db.refresh(review)
        return finding, review

    @staticmethod
    def apply_correction(
        db: Session, review_id: int, finding_id: int, user_id: Optional[int]
    ) -> ApplyCorrectionResponse:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found.")

        finding = (
            db.query(Finding)
            .filter(Finding.id == finding_id, Finding.review_id == review_id)
            .first()
        )
        if not finding:
            raise ValueError("Finding not found.")

        if not finding.suggested_correction:
            raise ValueError("Finding does not have a suggested correction to apply.")

        # Replace first occurrence of excerpt in working content
        original_excerpt = finding.excerpt
        replacement = finding.suggested_correction

        modified = False
        if original_excerpt in review.content:
            review.content = review.content.replace(original_excerpt, replacement, 1)
            modified = True
        elif original_excerpt == "[Missing Regulatory Disclaimer]" or "disclaimer" in finding.category.lower():
            to_append = replacement if replacement.startswith("\n\n") else f"\n\n{replacement}"
            clean_disc = " ".join(replacement.replace("\n", " ").split()).lower()
            clean_content = " ".join(review.content.split()).lower()
            if clean_disc not in clean_content and "disclaimer:" not in clean_content:
                review.content = review.content.rstrip() + to_append
                modified = True
            elif clean_disc in clean_content or "disclaimer:" in clean_content:
                # Already present without duplication
                modified = True
        else:
            # Case-insensitive replacement fallback
            import re
            pattern = re.compile(re.escape(original_excerpt), re.IGNORECASE)
            new_content, count = pattern.subn(replacement, review.content, count=1)
            if count > 0:
                review.content = new_content
                modified = True

        if not modified:
            raise ValueError(
                f"Cannot apply correction: Offending excerpt '{original_excerpt}' was not found in current working document."
            )

        finding.status = "applied"

        # Recalculate score & status with applied finding marked as resolved
        all_findings = db.query(Finding).filter(Finding.review_id == review_id).all()
        new_score, new_status = scoring_service.calculate_score(all_findings)
        review.compliance_score = new_score
        review.status = new_status

        activity = ReviewActivity(
            review_id=review_id,
            user_id=user_id,
            action="Correction Applied",
            details=f"Applied suggested correction '{replacement}'. Recalculated score: {new_score}/100.",
        )
        db.add(activity)
        db.commit()
        db.refresh(review)
        db.refresh(finding)

        return ApplyCorrectionResponse(
            review_id=review.id,
            finding_id=finding.id,
            finding_status=finding.status,
            updated_content=review.content,
            original_content=review.original_content,
            compliance_score=review.compliance_score,
            review_status=review.status,
        )


review_service = ReviewService()
