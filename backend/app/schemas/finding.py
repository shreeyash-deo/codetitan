from typing import Optional
from pydantic import BaseModel, ConfigDict


class FindingBase(BaseModel):
    severity: str = "warning"
    category: str
    excerpt: str
    explanation: str
    guideline_reference: Optional[str] = None
    suggested_correction: Optional[str] = None
    confidence: float = 1.0
    status: str = "open"


class FindingCreate(FindingBase):
    pass


class FindingOut(FindingBase):
    id: int
    review_id: int

    model_config = ConfigDict(from_attributes=True)
