from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.finding import FindingOut


class ContentVersionSummaryOut(BaseModel):
    id: int
    review_id: int
    version_number: int
    content_hash: str
    compliance_score: int
    status: str
    audit_status: str
    findings_count: int
    rule_set_version: Optional[str] = None
    summary: Optional[str] = None
    change_description: Optional[str] = None
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    version_state: Optional[str] = None  # "saved_draft", "audited", "submitted", "approved", "changes_requested"
    is_current: Optional[bool] = False
    is_original: Optional[bool] = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentVersionDetailOut(ContentVersionSummaryOut):
    content: str
    findings: List[FindingOut] = []


class DiffHunk(BaseModel):
    change_type: str  # "added", "removed", "unchanged"
    content: str
    old_start: Optional[int] = None
    old_lines: Optional[int] = None
    new_start: Optional[int] = None
    new_lines: Optional[int] = None


class FindingDelta(BaseModel):
    resolved: List[FindingOut] = []
    new: List[FindingOut] = []
    persistent: List[FindingOut] = []


class VersionComparisonOut(BaseModel):
    review_id: int
    source_version: ContentVersionSummaryOut
    target_version: ContentVersionSummaryOut
    score_before: int
    score_after: int
    score_delta: int
    audit_status_before: str
    audit_status_after: str
    text_diff: List[DiffHunk] = []
    raw_diff: str = ""
    findings_delta: FindingDelta
    source_content: Optional[str] = ""
    target_content: Optional[str] = ""
