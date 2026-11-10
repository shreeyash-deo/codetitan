from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.review import ContentReviewOut
from app.schemas.activity import ReviewActivityOut


class ViolationCategoryStat(BaseModel):
    category: str
    count: int
    percentage: float
    severity: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardStatsOut(BaseModel):
    total_reviews: int
    average_compliance_score: float
    has_reviews: bool = False
    pending_approvals: int
    approved_reviews: int
    reviews_needing_changes: int
    critical_findings: int
    total_approved_brand_rules: int
    pending_brand_rules: int
    uploaded_documents: int = 0
    violations_by_category: List[ViolationCategoryStat] = []
    recent_reviews: List[ContentReviewOut] = []
    recent_activity: List[ReviewActivityOut] = []

    model_config = ConfigDict(from_attributes=True)
