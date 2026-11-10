from typing import List
from pydantic import BaseModel, ConfigDict
from app.schemas.review import ContentReviewOut
from app.schemas.activity import ReviewActivityOut


class DashboardStatsOut(BaseModel):
    total_reviews: int
    average_compliance_score: float
    pending_approvals: int
    approved_reviews: int
    reviews_needing_changes: int
    critical_findings: int
    total_approved_brand_rules: int
    pending_brand_rules: int
    recent_reviews: List[ContentReviewOut]
    recent_activity: List[ReviewActivityOut]

    model_config = ConfigDict(from_attributes=True)
