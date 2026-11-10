from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import verify_workspace_access
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
    _: int = Depends(verify_workspace_access),
):
    """
    Returns aggregated real-time metrics:
    - Average compliance score
    - Total reviews & approval counts
    - Critical findings count
    - Total approved / pending brand rules
    - Recent review records
    - Live activity stream
    """
    return dashboard_service.get_dashboard_stats(db=db, workspace_id=workspace_id)
