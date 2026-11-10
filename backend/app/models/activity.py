from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import ContentReview
    from app.models.workspace import Workspace
    from app.models.user import User


class ReviewActivity(Base):
    __tablename__ = "review_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content_reviews.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped[Optional["ContentReview"]] = relationship("ContentReview", back_populates="activities")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activities")
    workspace: Mapped[Optional["Workspace"]] = relationship("Workspace")
