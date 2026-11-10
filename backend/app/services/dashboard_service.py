from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.rule import BrandRule
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.schemas.dashboard import DashboardStatsOut


class DashboardService:
    @staticmethod
    def get_dashboard_stats(db: Session, workspace_id: int) -> DashboardStatsOut:
        """
        Aggregate live database metrics for the executive governance dashboard.
        """
        # Reviews stats
        reviews_query = db.query(ContentReview).filter(ContentReview.workspace_id == workspace_id)
        total_reviews = reviews_query.count()

        avg_score_res = (
            db.query(func.avg(ContentReview.compliance_score))
            .filter(ContentReview.workspace_id == workspace_id)
            .scalar()
        )
        avg_score = round(float(avg_score_res), 1) if avg_score_res is not None else 100.0

        approved_reviews = (
            reviews_query.filter(ContentReview.status == "approved").count()
        )
        reviews_needing_changes = (
            reviews_query.filter(
                ContentReview.status.in_(["needs_changes", "needs_revision", "critical_issues"])
            ).count()
        )

        # Pending approvals (both reviews and rules)
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

        # Brand rules counts
        rules_query = db.query(BrandRule).filter(BrandRule.workspace_id == workspace_id)
        total_approved_brand_rules = rules_query.filter(BrandRule.approval_status == "approved").count()
        pending_brand_rules = rules_query.filter(BrandRule.approval_status == "pending").count()

        # Recent reviews (top 5)
        recent_reviews = (
            reviews_query.order_by(ContentReview.created_at.desc())
            .limit(5)
            .all()
        )

        # Recent activity (top 10)
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
            pending_approvals=pending_approvals,
            approved_reviews=approved_reviews,
            reviews_needing_changes=reviews_needing_changes,
            critical_findings=critical_findings,
            total_approved_brand_rules=total_approved_brand_rules,
            pending_brand_rules=pending_brand_rules,
            recent_reviews=recent_reviews,
            recent_activity=recent_activity,
        )


dashboard_service = DashboardService()
