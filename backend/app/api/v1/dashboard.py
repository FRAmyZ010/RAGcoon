from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_administrator
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import OverviewResponse, SystemVisitCreate, SystemVisitResponse
from app.services.dashboard_service import SEARCH_WINDOWS, get_overview, record_visit

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=OverviewResponse)
def read_overview(
    days: int = Query(7),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_administrator),
):
    if days not in SEARCH_WINDOWS:
        raise HTTPException(status_code=400, detail="เลือกได้แค่ 1, 7, 15 หรือ 30 วัน")
    return get_overview(db, days)


@router.post("/track-visit", response_model=SystemVisitResponse, status_code=201)
def track_visit(
    body: SystemVisitCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    ip_address = body.ip_address or (request.client.host if request.client else None)
    user_agent = body.user_agent or request.headers.get("user-agent")
    return record_visit(db, ip_address, user_agent)
