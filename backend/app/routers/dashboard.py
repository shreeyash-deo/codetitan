from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_workspace_member, get_current_user
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.dashboard import DashboardStatsOut
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/workspaces/{workspace_id}/dashboard", tags=["Executive Dashboard & Analytics"])


@router.get(
    "",
    response_model=DashboardStatsOut,
    status_code=status.HTTP_200_OK,
    summary="Get live workspace dashboard metrics, recent reviews, and activity timeline",
)
def get_dashboard_metrics(
    workspace_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_workspace_member),
    current_user: User = Depends(get_current_user),
):
    """
    Returns aggregated real-time metrics:
    - Average compliance score
    - Total reviews & approval counts
    - Critical findings count
    - Total approved / pending brand rules
    - Recent review records
    - Live activity stream
    Scoped for Employees to their own submissions.
    """
    return dashboard_service.get_dashboard_stats(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        role=member.role,
    )
