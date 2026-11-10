import secrets
import string
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.schemas.workspace import WorkspaceCreate


def normalize_workspace_role(role: str) -> str:
    r = role.strip().title()
    if r == "Editor":
        return "Employee"
    if r not in ("Admin", "Reviewer", "Employee"):
        raise ValueError(f"Invalid workspace role '{role}'. Allowed roles: Admin, Reviewer, Employee.")
    return r


class WorkspaceService:
    @staticmethod
    def generate_org_id(db: Session) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            candidate = f"ORG-{code}"
            if not db.query(Workspace).filter(Workspace.org_id == candidate).first():
                return candidate
        raise RuntimeError("Failed to generate a unique organisation ID after multiple attempts.")

    @staticmethod
    def create_workspace(db: Session, workspace_in: WorkspaceCreate, creator_id: int) -> Workspace:
        org_id = WorkspaceService.generate_org_id(db)
        workspace = Workspace(name=workspace_in.name, org_id=org_id)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        # Creator automatically becomes an Admin of this workspace
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=creator_id,
            role="Admin",
        )
        db.add(membership)
        db.commit()
        db.refresh(workspace)
        return workspace

    @staticmethod
    def list_workspaces_for_user(db: Session, user: User) -> List[Workspace]:
        # Scoped strictly to workspaces where user has explicit active membership
        return (
            db.query(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .filter(WorkspaceMember.user_id == user.id)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, workspace_id: int) -> Optional[Workspace]:
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()

    @staticmethod
    def get_by_org_id(db: Session, org_id: str) -> Optional[Workspace]:
        return db.query(Workspace).filter(Workspace.org_id == org_id.strip()).first()

    @staticmethod
    def is_member(db: Session, workspace_id: int, user_id: int) -> bool:
        return (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
            is not None
        )

    @staticmethod
    def get_member(db: Session, workspace_id: int, user_id: int) -> Optional[WorkspaceMember]:
        return (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )

    @staticmethod
    def add_member(
        db: Session, workspace_id: int, user_id: int, role: str = "Employee"
    ) -> WorkspaceMember:
        norm_role = normalize_workspace_role(role)
        existing = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )
        if existing:
            existing.role = norm_role
            db.commit()
            db.refresh(existing)
            return existing

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=norm_role,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership


workspace_service = WorkspaceService()
