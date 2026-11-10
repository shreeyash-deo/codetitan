from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import ContentReview
    from app.models.rule import BrandRule
    from app.models.user import User


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("content_reviews.id", ondelete="CASCADE"), nullable=True, index=True
    )
    brand_rule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brand_rules.id", ondelete="CASCADE"), nullable=True, index=True
    )
    submitted_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    review: Mapped[Optional["ContentReview"]] = relationship("ContentReview", back_populates="approvals")
    brand_rule: Mapped[Optional["BrandRule"]] = relationship("BrandRule", back_populates="approvals")
    submitter: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[submitted_by], back_populates="submitted_approvals"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewer_id], back_populates="reviewed_approvals"
    )
