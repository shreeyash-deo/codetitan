from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review import ContentReview


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("content_reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(50), default="warning", nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    guideline_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)

    # Relationships
    review: Mapped["ContentReview"] = relationship("ContentReview", back_populates="findings")
