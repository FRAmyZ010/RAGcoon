from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.feedback import Feedback
from app.models.project import Project
from app.models.search_query import SearchQuery
from app.models.system_visit import SystemVisit
from app.models.user import User

SEARCH_WINDOWS = (1, 7, 15, 30)
TOP_KEYWORD_LIMIT = 10
BANGKOK = ZoneInfo("Asia/Bangkok")


def range_start(days: int) -> datetime:
    now = datetime.now(BANGKOK)
    start_day = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start_day.astimezone(timezone.utc)


def count_keywords(values: list[str | None], limit: int = TOP_KEYWORD_LIMIT) -> list[dict]:
    counts: dict[str, dict] = {}
    for raw in values:
        if not raw:
            continue
        for part in raw.split(","):
            word = part.strip()
            if not word:
                continue
            key = word.casefold()
            bucket = counts.setdefault(key, {"keyword": word, "count": 0})
            bucket["count"] += 1
    ranked = sorted(counts.values(), key=lambda item: (-item["count"], item["keyword"].casefold()))
    return ranked[:limit]


def record_visit(db: Session, ip_address: str | None, user_agent: str | None) -> SystemVisit:
    agent = (user_agent or "").strip()[:255] or None
    row = SystemVisit(ip_address=(ip_address or "").strip() or None, user_agent=agent)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_overview(db: Session, days: int = 7) -> dict:
    window = days if days in SEARCH_WINDOWS else 7
    start = range_start(window)
    day = func.date(SearchQuery.created_at)
    search_rows = (
        db.query(day, func.count(SearchQuery.id))
        .filter(SearchQuery.created_at >= start)
        .group_by(day)
        .order_by(day)
        .all()
    )
    year_rows = (
        db.query(Project.academic_year, func.count(Document.id))
        .join(Document, Document.project_id == Project.id)
        .group_by(Project.academic_year)
        .order_by(Project.academic_year.desc().nullslast())
        .all()
    )
    keyword_values = [row[0] for row in db.query(Document.keywords).all()]
    viewed_rows = (
        db.query(Document)
        .filter(Document.view_count > 0)
        .order_by(Document.view_count.desc(), Document.filename.asc())
        .limit(10)
        .all()
    )
    return {
        "total_documents": db.query(func.count(Document.id)).scalar() or 0,
        "total_projects": db.query(func.count(Project.id)).scalar() or 0,
        "total_queries": db.query(func.count(SearchQuery.id)).scalar() or 0,
        "total_feedbacks": db.query(func.count(Feedback.id)).scalar() or 0,
        "total_visits": db.query(func.count(SystemVisit.id)).scalar() or 0,
        "feedbacks_in_range": db.query(func.count(Feedback.id)).filter(Feedback.created_at >= start).scalar() or 0,
        "visits_in_range": db.query(func.count(SystemVisit.id)).filter(SystemVisit.visited_at >= start).scalar() or 0,
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "documents_by_year": [{"year": year, "count": count} for year, count in year_rows],
        "searches_by_day": [
            {"day": day_value.isoformat(), "count": count}
            for day_value, count in search_rows
            if day_value is not None
        ],
        "top_keywords": count_keywords(keyword_values),
        "most_viewed": [
            {
                "document_id": row.id,
                "title": row.title,
                "filename": row.filename,
                "view_count": row.view_count or 0,
            }
            for row in viewed_rows
        ],
    }
