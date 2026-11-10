from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.workspace_member import WorkspaceMember
    from app.models.guideline import GuidelineDocument
    from app.models.rule import BrandRule
    from app.models.review import ContentReview


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )
    guidelines: Mapped[List["GuidelineDocument"]] = relationship(
        "GuidelineDocument", back_populates="workspace", cascade="all, delete-orphan"
    )
    brand_rules: Mapped[List["BrandRule"]] = relationship(
        "BrandRule", back_populates="workspace", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["ContentReview"]] = relationship(
        "ContentReview", back_populates="workspace", cascade="all, delete-orphan"
    )
