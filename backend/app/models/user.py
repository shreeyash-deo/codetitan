from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.workspace_member import WorkspaceMember
    from app.models.review import ContentReview
    from app.models.approval import Approval
    from app.models.activity import ReviewActivity


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="User", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace_memberships: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )
    submitted_reviews: Mapped[List["ContentReview"]] = relationship(
        "ContentReview", back_populates="submitter"
    )
    submitted_approvals: Mapped[List["Approval"]] = relationship(
        "Approval", foreign_keys="Approval.submitted_by", back_populates="submitter"
    )
    reviewed_approvals: Mapped[List["Approval"]] = relationship(
        "Approval", foreign_keys="Approval.reviewer_id", back_populates="reviewer"
    )
    activities: Mapped[List["ReviewActivity"]] = relationship(
        "ReviewActivity", back_populates="user"
    )
