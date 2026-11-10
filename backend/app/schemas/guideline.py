from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class GuidelineDocumentBase(BaseModel):
    filename: str


class GuidelineDocumentCreate(GuidelineDocumentBase):
    file_path: str
    extracted_text: Optional[str] = None
    status: Optional[str] = "pending"


class GuidelineDocumentOut(GuidelineDocumentBase):
    id: int
    workspace_id: int
    file_path: str
    extracted_text: Optional[str] = None
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
