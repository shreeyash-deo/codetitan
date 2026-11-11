from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.rule import BrandRule
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.models.guideline import GuidelineDocument
from app.models.workspace_member import WorkspaceMember
from app.schemas.dashboard import DashboardStatsOut, ViolationCategoryStat


class DashboardService:
    @staticmethod
    def get_dashboard_stats(
        db: Session,
        workspace_id: int,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
    ) -> DashboardStatsOut:
        """
        Aggregate live database metrics for the executive governance dashboard.
        Scoped to personal submissions when the caller has the Employee role.
        """
        if role is None and user_id is not None:
            member = (
                db.query(WorkspaceMember)
                .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
                .first()
            )
            if member:
                role = member.role

        is_employee = bool(role and role.strip().lower() in ("employee", "editor")) and (user_id is not None)

        # Reviews stats
        reviews_query = db.query(ContentReview).filter(ContentReview.workspace_id == workspace_id)
        if is_employee:
            reviews_query = reviews_query.filter(ContentReview.submitted_by == user_id)

        total_reviews = reviews_query.count()
        has_reviews = total_reviews > 0

        if is_employee:
            avg_score_res = (
                db.query(func.avg(ContentReview.compliance_score))
                .filter(
                    ContentReview.workspace_id == workspace_id,
                    ContentReview.submitted_by == user_id,
                )
                .scalar()
            )
        else:
            avg_score_res = (
                db.query(func.avg(ContentReview.compliance_score))
                .filter(ContentReview.workspace_id == workspace_id)
                .scalar()
            )
        avg_score = round(float(avg_score_res), 1) if (avg_score_res is not None and has_reviews) else 100.0

        approved_reviews = (
            reviews_query.filter(ContentReview.status == "approved").count()
        )
        reviews_needing_changes = (
            reviews_query.filter(
                ContentReview.status.in_(["needs_changes", "needs_revision", "critical_issues"])
            ).count()
        )

        # Uploaded guideline documents
        if is_employee:
            uploaded_documents = 0
        else:
            uploaded_documents = (
                db.query(GuidelineDocument)
                .filter(GuidelineDocument.workspace_id == workspace_id)
                .count()
            )

        # Pending approvals (both reviews and rules for admin/reviewer; only personal reviews for employee)
        if is_employee:
            pending_approvals = (
                db.query(Approval)
                .join(ContentReview, Approval.review_id == ContentReview.id)
                .filter(
                    ContentReview.workspace_id == workspace_id,
                    ContentReview.submitted_by == user_id,
                    Approval.status == "pending",
                )
                .count()
            )
        else:
            pending_approvals = (
                db.query(Approval)
                .outerjoin(ContentReview, Approval.review_id == ContentReview.id)
                .outerjoin(BrandRule, Approval.brand_rule_id == BrandRule.id)
                .filter(
                    or_(
                        ContentReview.workspace_id == workspace_id,
                        BrandRule.workspace_id == workspace_id,
                    ),
                    Approval.status == "pending",
                )
                .count()
            )

        # Critical findings across active reviews in workspace
        if is_employee:
            critical_findings = (
                db.query(Finding)
                .join(ContentReview, Finding.review_id == ContentReview.id)
                .filter(
                    ContentReview.workspace_id == workspace_id,
                    ContentReview.submitted_by == user_id,
                    Finding.severity == "critical",
                    Finding.status == "open",
                )
                .count()
            )
        else:
            critical_findings = (
                db.query(Finding)
                .join(ContentReview, Finding.review_id == ContentReview.id)
                .filter(
                    ContentReview.workspace_id == workspace_id,
                    Finding.severity == "critical",
                    Finding.status == "open",
                )
                .count()
            )

        # Violation breakdown by category & severity
        if is_employee:
            findings_grouped = (
                db.query(Finding.category, Finding.severity, func.count(Finding.id))
                .join(ContentReview, Finding.review_id == ContentReview.id)
                .filter(
                    ContentReview.workspace_id == workspace_id,
                    ContentReview.submitted_by == user_id,
                )
                .group_by(Finding.category, Finding.severity)
                .all()
            )
        else:
            findings_grouped = (
                db.query(Finding.category, Finding.severity, func.count(Finding.id))
                .join(ContentReview, Finding.review_id == ContentReview.id)
                .filter(ContentReview.workspace_id == workspace_id)
                .group_by(Finding.category, Finding.severity)
                .all()
            )

        total_findings_count = sum(row[2] for row in findings_grouped)
        category_map = {}
        for cat, sev, cnt in findings_grouped:
            c_name = cat or "General Compliance"
            if c_name not in category_map:
                category_map[c_name] = {"count": 0, "severities": {}}
            category_map[c_name]["count"] += cnt
            category_map[c_name]["severities"][sev] = category_map[c_name]["severities"].get(sev, 0) + cnt

        violations_by_category = []
        for c_name, data in sorted(category_map.items(), key=lambda x: x[1]["count"], reverse=True):
            cnt = data["count"]
            pct = round((cnt / total_findings_count) * 100, 1) if total_findings_count > 0 else 0.0
            sevs = data["severities"]
            dominant_sev = (
                "critical"
                if sevs.get("critical", 0) > 0
                else ("moderate" if sevs.get("moderate", 0) > 0 else "minor")
            )
            violations_by_category.append(
                ViolationCategoryStat(
                    category=c_name,
                    count=cnt,
                    percentage=pct,
                    severity=dominant_sev,
                    description=f"Identified across audited copy in {c_name.lower()}.",
                )
            )

        # Brand rules counts
        rules_query = db.query(BrandRule).filter(BrandRule.workspace_id == workspace_id)
        total_approved_brand_rules = rules_query.filter(BrandRule.approval_status == "approved").count()
        if is_employee:
            pending_brand_rules = 0
        else:
            pending_brand_rules = rules_query.filter(BrandRule.approval_status == "pending").count()

        # Recent reviews (top 5)
        recent_reviews = (
            reviews_query.order_by(ContentReview.created_at.desc())
            .limit(5)
            .all()
        )

        # Recent activity (top 10)
        if is_employee:
            recent_activity = (
                db.query(ReviewActivity)
                .outerjoin(ContentReview, ReviewActivity.review_id == ContentReview.id)
                .filter(
                    or_(
                        ReviewActivity.user_id == user_id,
                        and_(
                            ContentReview.workspace_id == workspace_id,
                            ContentReview.submitted_by == user_id,
                        ),
                    )
                )
                .order_by(ReviewActivity.created_at.desc())
                .limit(10)
                .all()
            )
        else:
            recent_activity = (
                db.query(ReviewActivity)
                .outerjoin(ContentReview, ReviewActivity.review_id == ContentReview.id)
                .filter(
                    or_(
                        ReviewActivity.workspace_id == workspace_id,
                        ContentReview.workspace_id == workspace_id,
                    )
                )
                .order_by(ReviewActivity.created_at.desc())
                .limit(10)
                .all()
            )

        return DashboardStatsOut(
            total_reviews=total_reviews,
            average_compliance_score=avg_score,
            has_reviews=has_reviews,
            pending_approvals=pending_approvals,
            approved_reviews=approved_reviews,
            reviews_needing_changes=reviews_needing_changes,
            critical_findings=critical_findings,
            total_approved_brand_rules=total_approved_brand_rules,
            pending_brand_rules=pending_brand_rules,
            uploaded_documents=uploaded_documents,
            violations_by_category=violations_by_category,
            recent_reviews=recent_reviews,
            recent_activity=recent_activity,
        )


dashboard_service = DashboardService()
