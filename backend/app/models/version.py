from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import ContentReview
    from app.models.user import User
    from app.models.finding import Finding


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("content_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    compliance_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_review", nullable=False)
    audit_status: Mapped[str] = mapped_column(String(50), nullable=False)
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rule_set_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    change_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("review_id", "version_number", name="uq_content_versions_review_version"),
    )

    # Relationships
    review: Mapped["ContentReview"] = relationship("ContentReview", back_populates="versions")
    author: Mapped[Optional["User"]] = relationship("User")
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="version", cascade="all, delete-orphan"
    )
