import secrets
import string
from typing import List, Optional, Dict, Any
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
    def create_workspace(
        db: Session,
        workspace_in: Optional[WorkspaceCreate] = None,
        creator_id: int = 0,
        name: Optional[str] = None,
    ) -> Workspace:
        ws_name = name if name is not None else (workspace_in.name if workspace_in else "New Organisation")
        org_id = WorkspaceService.generate_org_id(db)
        workspace = Workspace(name=ws_name, org_id=org_id)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        # Creator automatically becomes an Admin of this workspace with approved status
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=creator_id,
            role="Admin",
            status="approved",
        )
        db.add(membership)
        db.commit()
        db.refresh(workspace)
        return workspace

    @staticmethod
    def list_workspaces_for_user(db: Session, user: User) -> List[Workspace]:
        # Scoped strictly to workspaces where user has explicit approved membership
        return (
            db.query(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .filter(WorkspaceMember.user_id == user.id, WorkspaceMember.status == "approved")
            .all()
        )

    @staticmethod
    def list_user_pending_requests(db: Session, user: User) -> List[Dict[str, Any]]:
        """List organisations where the user has submitted a join request that is currently pending."""
        memberships = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.user_id == user.id, WorkspaceMember.status == "pending")
            .all()
        )
        results = []
        for m in memberships:
            ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
            if ws:
                results.append({
                    "workspace_id": ws.id,
                    "org_id": ws.org_id,
                    "org_name": ws.name,
                    "role": m.role,
                    "status": m.status,
                })
        return results

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
                WorkspaceMember.status == "approved",
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
        db: Session, workspace_id: int, user_id: int, role: str = "Employee", status: str = "approved"
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
            existing.status = status
            db.commit()
            db.refresh(existing)
            return existing

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=norm_role,
            status=status,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    @staticmethod
    def request_join(db: Session, org_id: str, user_id: int) -> WorkspaceMember:
        """
        Submit a request to join an organisation via ORG-XXXXXXXX.
        Always requests Employee role with pending status.
        Never allows self-assignment of Admin or Reviewer.
        """
        clean_org_id = org_id.strip().upper()
        workspace = WorkspaceService.get_by_org_id(db, clean_org_id)
        if not workspace:
            raise ValueError(f"Organisation ID '{org_id}' not found. Please verify the code.")

        existing = WorkspaceService.get_member(db, workspace.id, user_id)
        if existing:
            if existing.status == "approved":
                raise ValueError("You are already an active member of this organisation.")
            if existing.status == "pending":
                raise ValueError("You already have a pending membership request for this organisation.")

        # Create pending membership with default Employee role
        membership = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role="Employee",
            status="pending",
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        return membership

    @staticmethod
    def list_pending_requests(db: Session, workspace_id: int) -> List[Dict[str, Any]]:
        """List all pending membership requests for a workspace (Admins only)."""
        pending_members = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "pending",
            )
            .all()
        )
        results = []
        for m in pending_members:
            user = db.query(User).filter(User.id == m.user_id).first()
            if user:
                results.append({
                    "id": m.id,
                    "workspace_id": m.workspace_id,
                    "user_id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": m.role,
                    "status": m.status,
                })
        return results

    @staticmethod
    def approve_request(
        db: Session, workspace_id: int, target_user_id: int, admin_user: User
    ) -> WorkspaceMember:
        """Approve a pending membership request. Grants Employee access by default."""
        if target_user_id == admin_user.id:
            raise ValueError("You cannot approve your own membership request.")

        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
                WorkspaceMember.status == "pending",
            )
            .first()
        )
        if not member:
            raise ValueError("Pending membership request not found.")

        member.status = "approved"
        member.role = "Employee"
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def reject_request(
        db: Session, workspace_id: int, target_user_id: int, admin_user: User
    ) -> None:
        """
        Reject a pending membership request.
        Deletes the pending membership record so the user can request again in the future.
        """
        if target_user_id == admin_user.id:
            raise ValueError("You cannot reject your own membership request.")

        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
                WorkspaceMember.status == "pending",
            )
            .first()
        )
        if not member:
            raise ValueError("Pending membership request not found.")

        db.delete(member)
        db.commit()

    @staticmethod
    def cancel_join_request(db: Session, workspace_id: int, user_id: int) -> None:
        """
        Cancel a user's own pending membership request.
        Deletes the pending membership record so the user can request again or join a different org.
        """
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "pending",
            )
            .first()
        )
        if not member:
            raise ValueError("Pending membership request not found.")

        db.delete(member)
        db.commit()

    @staticmethod
    def update_member_role(
        db: Session, workspace_id: int, target_user_id: int, new_role: str, admin_user: User
    ) -> WorkspaceMember:
        """
        Admin can promote Employee to Reviewer or demote Reviewer to Employee.
        Prevents self-demotion of the current Admin.
        Does not allow public or peer Admin promotion through standard role management.
        """
        if target_user_id == admin_user.id:
            raise ValueError("Admins cannot change their own role to prevent accidental lockout.")

        norm_role = new_role.strip().title()
        if norm_role not in ("Employee", "Reviewer"):
            raise ValueError("Allowed role updates are 'Employee' and 'Reviewer'.")

        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
                WorkspaceMember.status == "approved",
            )
            .first()
        )
        if not member:
            raise ValueError("Active workspace member not found.")

        member.role = norm_role
        db.commit()
        db.refresh(member)
        return member


workspace_service = WorkspaceService()
