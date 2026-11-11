import math
import hashlib
from datetime import datetime, timezone
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
from app.schemas.finding import FindingOut
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

        # Compute SHA-256 hash of submitted content
        content_hash = hashlib.sha256(submission.content.strip().encode("utf-8")).hexdigest()

        # Persist ContentReview
        review = ContentReview(
            workspace_id=workspace_id,
            title=submission.title.strip(),
            content=submission.content,
            original_content=submission.content,  # Preserve immutable original
            content_type=submission.content_type,
            status=audit_result.status,
            compliance_score=audit_result.compliance_score,
            audit_status="verified",
            audited_content_hash=content_hash,
            audited_at=datetime.now(timezone.utc),
            findings_count=len(audit_result.findings),
            rule_set_version=f"rules_count:{len(approved_rules)}",
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
        review.updated_content = review.content
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
        submitted_by: Optional[int] = None,
    ) -> PaginatedReviewsOut:
        query = db.query(ContentReview).filter(ContentReview.workspace_id == workspace_id)

        if submitted_by is not None:
            query = query.filter(ContentReview.submitted_by == submitted_by)

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
    def recheck_and_audit(
        db: Session,
        review_id: int,
        new_content: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> ContentReview:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found.")

        content_to_audit = (new_content if new_content is not None else review.content).strip()
        if not content_to_audit:
            raise ValueError("Content cannot be empty.")

        # Update working content (never touching immutable original_content)
        review.content = new_content if new_content is not None else review.content

        # Fetch approved brand rules for workspace
        approved_rules = (
            db.query(BrandRule)
            .filter(
                BrandRule.workspace_id == review.workspace_id,
                BrandRule.approval_status == "approved",
            )
            .all()
        )

        if not approved_rules:
            review.audit_status = "rules_unavailable"
            review.compliance_score = 0
            review.summary = "No approved brand rules found. Brand-specific compliance analysis cannot be completed."
            db.commit()
            db.refresh(review)
            return review

        try:
            audit_result = compliance_engine.run_compliance_audit(
                content=content_to_audit,
                content_type=review.content_type,
                approved_rules=approved_rules,
            )
        except Exception as exc:
            review.audit_status = "failed"
            review.summary = f"Compliance audit failed: {exc}"
            db.commit()
            db.refresh(review)
            raise

        content_hash = hashlib.sha256(content_to_audit.encode("utf-8")).hexdigest()

        # Update review properties atomically
        review.compliance_score = audit_result.compliance_score
        review.status = audit_result.status
        review.audit_status = "verified"
        review.audited_content_hash = content_hash
        review.audited_at = datetime.now(timezone.utc)
        review.summary = audit_result.summary
        review.rule_set_version = f"rules_count:{len(approved_rules)}"
        review.findings_count = len(audit_result.findings)

        # Synchronize findings without deleting existing instances (preserves object identity & history)
        existing_findings = db.query(Finding).filter(Finding.review_id == review.id).all()
        existing_by_sig = {
            (ef.excerpt.strip().lower(), ef.category.strip().lower()): ef
            for ef in existing_findings
        }
        active_sigs = set()

        for f in audit_result.findings:
            sig = (f.excerpt.strip().lower(), f.category.strip().lower())
            active_sigs.add(sig)
            if sig in existing_by_sig:
                ef = existing_by_sig[sig]
                ef.severity = f.severity
                ef.explanation = f.explanation
                ef.guideline_reference = f.guideline_reference
                ef.suggested_correction = f.suggested_correction
                ef.confidence = f.confidence
                ef.status = "open"
            else:
                new_f = Finding(
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
                db.add(new_f)

        # Findings that are no longer active in the audited content are marked applied
        for ef in existing_findings:
            sig = (ef.excerpt.strip().lower(), ef.category.strip().lower())
            if sig not in active_sigs:
                ef.status = "applied"

        activity = ReviewActivity(
            review_id=review.id,
            user_id=user_id,
            action="Audit Completed",
            details=f"Compliance audit re-verified. Score: {review.compliance_score}/100. Violations: {len(audit_result.findings)}.",
        )
        db.add(activity)

        db.commit()
        db.refresh(review)
        review.updated_content = review.content
        return review

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
        new_text = review.content
        if original_excerpt in new_text:
            new_text = new_text.replace(original_excerpt, replacement, 1)
            modified = True
        elif original_excerpt == "[Missing Regulatory Disclaimer]" or "disclaimer" in finding.category.lower():
            to_append = replacement if replacement.startswith("\n\n") else f"\n\n{replacement}"
            clean_disc = " ".join(replacement.replace("\n", " ").split()).lower()
            clean_content = " ".join(new_text.split()).lower()
            if clean_disc not in clean_content and "disclaimer:" not in clean_content:
                new_text = new_text.rstrip() + to_append
                modified = True
            elif clean_disc in clean_content or "disclaimer:" in clean_content:
                # Already present without duplication
                modified = True
        else:
            # Case-insensitive replacement fallback
            import re
            pattern = re.compile(re.escape(original_excerpt), re.IGNORECASE)
            new_c, count = pattern.subn(replacement, new_text, count=1)
            if count > 0:
                new_text = new_c
                modified = True

        if not modified:
            raise ValueError(
                f"Cannot apply correction: Offending excerpt '{original_excerpt}' was not found in current working document."
            )

        activity = ReviewActivity(
            review_id=review_id,
            user_id=user_id,
            action="Correction Applied",
            details=f"Applied suggested correction '{replacement}'. Re-auditing content.",
        )
        db.add(activity)

        # Run FULL compliance engine on the actual corrected text
        review = ReviewService.recheck_and_audit(
            db=db,
            review_id=review_id,
            new_content=new_text,
            user_id=user_id,
        )
        finding.status = "applied"
        db.commit()
        db.refresh(review)
        db.refresh(finding)

        all_findings = db.query(Finding).filter(Finding.review_id == review_id).all()
        return ApplyCorrectionResponse(
            review_id=review.id,
            finding_id=finding.id,
            finding_status=finding.status,
            updated_content=review.content,
            content=review.content,
            original_content=review.original_content,
            compliance_score=review.compliance_score,
            review_status=review.status,
            audit_status=review.audit_status,
            audited_content_hash=review.audited_content_hash,
            audited_at=review.audited_at,
            findings=[FindingOut.model_validate(f) for f in all_findings],
        )

    @staticmethod
    def batch_apply_corrections(
        db: Session, review_id: int, user_id: Optional[int]
    ) -> ContentReview:
        review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
        if not review:
            raise ValueError("Review not found.")

        findings = (
            db.query(Finding)
            .filter(Finding.review_id == review_id, Finding.status == "open")
            .all()
        )
        if not findings:
            return review

        updated_content = review.content
        disclaimer_to_append = ""
        applied_count = 0

        for f in findings:
            if not f.suggested_correction:
                continue
            orig = f.excerpt
            repl = f.suggested_correction

            if orig == "[Missing Regulatory Disclaimer]" or "disclaimer" in f.category.lower():
                to_append = repl if repl.startswith("\n\n") else f"\n\n{repl}"
                clean_disc = " ".join(repl.replace("\n", " ").split()).lower()
                clean_content = " ".join(updated_content.split()).lower()
                if clean_disc not in clean_content and "disclaimer:" not in clean_content:
                    disclaimer_to_append = to_append
                f.status = "applied"
                applied_count += 1
            elif orig in updated_content:
                updated_content = updated_content.replace(orig, repl, 1)
                f.status = "applied"
                applied_count += 1
            else:
                import re
                pattern = re.compile(re.escape(orig), re.IGNORECASE)
                new_c, count = pattern.subn(repl, updated_content, count=1)
                if count > 0:
                    updated_content = new_c
                    f.status = "applied"
                    applied_count += 1

        if disclaimer_to_append:
            updated_content = updated_content.rstrip() + disclaimer_to_append

        # Run FULL compliance engine on the batch-corrected text
        review = ReviewService.recheck_and_audit(
            db=db,
            review_id=review_id,
            new_content=updated_content,
            user_id=user_id,
        )

        activity = ReviewActivity(
            review_id=review_id,
            user_id=user_id,
            action="Batch Corrections Applied",
            details=f"Applied {applied_count} correction(s) to working draft. Re-audited score: {review.compliance_score}/100.",
        )
        db.add(activity)
        db.commit()
        db.refresh(review)
        review.updated_content = review.content
        return review


review_service = ReviewService()
