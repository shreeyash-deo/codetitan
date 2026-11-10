from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.user import User
    from app.models.finding import Finding
    from app.models.approval import Approval
    from app.models.activity import ReviewActivity


class ContentReview(Base):
    __tablename__ = "content_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_review", nullable=False, index=True)
    compliance_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="reviews")
    submitter: Mapped[Optional["User"]] = relationship("User", back_populates="submitted_reviews")
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="review", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="review", cascade="all, delete-orphan"
    )
    activities: Mapped[List["ReviewActivity"]] = relationship(
        "ReviewActivity", back_populates="review", cascade="all, delete-orphan"
    )
