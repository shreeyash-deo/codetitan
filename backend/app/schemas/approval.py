from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserOut


class ApprovalBase(BaseModel):
    status: str = "pending"
    comment: Optional[str] = None


class ApprovalCreate(ApprovalBase):
    review_id: Optional[int] = None
    brand_rule_id: Optional[int] = None
    reviewer_id: Optional[int] = None


class RequestApprovalPayload(BaseModel):
    comment: Optional[str] = Field(None, description="Optional note for the reviewer")
    reviewer_id: Optional[int] = Field(None, description="Specific reviewer assignment")


class RequestChangesPayload(BaseModel):
    comment: str = Field(..., min_length=1, description="Mandatory revision instructions")


class RejectApprovalPayload(BaseModel):
    reason: str = Field(..., min_length=1, description="Mandatory rejection reason")


class ApprovalOut(ApprovalBase):
    id: int
    review_id: Optional[int] = None
    brand_rule_id: Optional[int] = None
    submitted_by: Optional[int] = None
    reviewer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    submitter: Optional[UserOut] = None
    reviewer: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
