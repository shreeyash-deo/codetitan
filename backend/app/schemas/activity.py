from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserOut


class ReviewActivityOut(BaseModel):
    id: int
    review_id: int
    user_id: Optional[int] = None
    action: str
    details: Optional[str] = None
    created_at: datetime
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
