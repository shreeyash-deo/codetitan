from typing import Callable, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the incoming bearer token and load the current user from database.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Legacy system user role checker (e.g. platform admin).
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_lower = current_user.role.lower()
        allowed_roles_lower = [r.lower() for r in allowed_roles]
        if user_role_lower not in allowed_roles_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


def get_workspace_member(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMember:
    """
    Verify caller has active membership in the workspace.
    Global account roles NEVER bypass this check.
    """
    member = workspace_service.get_member(db, workspace_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace",
        )
    return member


def verify_workspace_access(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_workspace_member),
) -> int:
    """
    Ensure the current user is an active member of the workspace.
    """
    return workspace_id


def require_workspace_role(*allowed_roles: str) -> Callable:
    """
    Dependency factory to enforce workspace-scoped roles (Admin, Reviewer, Employee).
    """
    allowed_lower = [r.lower() for r in allowed_roles]
    if "employee" in allowed_lower and "editor" not in allowed_lower:
        allowed_lower.append("editor")

    def role_checker(
        workspace_id: int,
        member: WorkspaceMember = Depends(get_workspace_member),
    ) -> WorkspaceMember:
        if member.role.lower() not in allowed_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required workspace role: {', '.join(allowed_roles)}",
            )
        return member

    return role_checker


require_workspace_admin = require_workspace_role("Admin")
require_workspace_reviewer_or_admin = require_workspace_role("Admin", "Reviewer")
