from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ExtractedRuleCandidate(BaseModel):
    title: str = Field(..., description="Concise rule title")
    description: str = Field(..., description="Actionable guideline or restriction")
    category: str = Field(..., description="Rule category")
    source_reference: Optional[str] = Field(None, description="Page or section citation in document")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    subCategory: Optional[str] = Field(None, description="Detailed subcategory topic")
    rationale: Optional[str] = Field(None, description="Rule justification and risk rationale")
    severity: Optional[str] = Field(None, description="critical, high, medium, or low")
    enforcement_level: Optional[str] = Field(None, description="Strict or Advisory")
    approved_example: Optional[str] = Field(None, description="Recommended compliant phrasing")
    prohibited_example: Optional[str] = Field(None, description="Explicitly non-compliant phrasing")


class ExtractedRulesResponse(BaseModel):
    document_id: int
    extracted_count: int
    rules: List["BrandRuleOut"]


class BrandRuleBase(BaseModel):
    title: str
    description: str
    category: str
    source_reference: Optional[str] = None
    confidence: float = 1.0
    approval_status: str = "pending"


class BrandRuleCreate(BrandRuleBase):
    document_id: Optional[int] = None


class BrandRuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    source_reference: Optional[str] = None
    confidence: Optional[float] = None
    approval_status: Optional[str] = None


class BrandRuleOut(BrandRuleBase):
    id: int
    workspace_id: int
    document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
