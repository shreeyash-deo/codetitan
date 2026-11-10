from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserOut
from app.schemas.finding import FindingOut, FindingCreate
from app.schemas.activity import ReviewActivityOut
from app.schemas.approval import ApprovalOut

ContentType = Literal[
    "social_media",
    "website",
    "email",
    "advertisement",
    "blog",
    "other",
]


class ContentReviewBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    content_type: str = "social_media"


class ContentReviewSubmission(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Asset title")
    content: str = Field(..., min_length=1, description="Raw marketing copy or text to audit")
    content_type: str = Field(
        "social_media",
        description="One of: social_media, website, email, advertisement, blog, other",
    )


class ContentReviewCreate(ContentReviewBase):
    findings: Optional[List[FindingCreate]] = None


class ContentReviewUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    compliance_score: Optional[int] = None
    summary: Optional[str] = None


class ContentReviewOut(ContentReviewBase):
    id: int
    workspace_id: int
    original_content: str
    status: str
    compliance_score: int
    audit_status: str = "verified"
    audited_content_hash: Optional[str] = None
    audited_at: Optional[datetime] = None
    findings_count: int = 0
    rule_set_version: Optional[str] = None
    summary: Optional[str] = None
    submitted_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    submitter: Optional[UserOut] = None
    findings: Optional[List[FindingOut]] = None
    approvals: Optional[List[ApprovalOut]] = None
    activities: Optional[List[ReviewActivityOut]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedReviewsOut(BaseModel):
    items: List[ContentReviewOut]
    total: int
    page: int
    size: int
    pages: int


class ApplyCorrectionResponse(BaseModel):
    review_id: int
    finding_id: int
    finding_status: str
    updated_content: str
    original_content: str
    compliance_score: int
    review_status: str
    audit_status: str = "verified"
    audited_content_hash: Optional[str] = None
    audited_at: Optional[datetime] = None
    findings: Optional[List[FindingOut]] = None
