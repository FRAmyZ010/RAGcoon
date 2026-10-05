import os
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.search_query import SearchQuery

UPLOAD_DIR = "storage/feedback"
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENT_MB = MAX_ATTACHMENT_BYTES // (1024 * 1024)
ALLOWED_TYPES = {"Suggestion", "Bug", "Others"}
ALLOWED_STATUSES = {"Open", "In Progress", "Resolved"}


class FeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_submission(
    *,
    name: str,
    rating: int,
    feedback_type: str,
    comment: str,
) -> dict:
    submitter_name = (name or "").strip()
    if not submitter_name:
        raise FeedbackError("Please enter your name.")
    if len(submitter_name) > 120:
        raise FeedbackError("Name is too long.")
    if rating not in {1, 2, 3, 4, 5}:
        raise FeedbackError("Please select a rating.")
    if feedback_type not in ALLOWED_TYPES:
        raise FeedbackError("Please select a feedback type.")
    text = (comment or "").strip()
    if not text:
        raise FeedbackError("Please enter your feedback.")
    return {
        "submitter_name": submitter_name,
        "rating": rating,
        "feedback_type": feedback_type,
        "comment": text,
    }


def _safe_filename(filename: str) -> str:
    base = os.path.basename(filename or "").replace(" ", "_")
    cleaned = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
    return cleaned or "attachment"


def save_attachment(filename: str, content: bytes) -> tuple[str, str]:
    if not content:
        raise FeedbackError("ไฟล์แนบว่างเปล่า")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise FeedbackError(f"ไฟล์แนบเกิน {MAX_ATTACHMENT_MB}MB")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{_safe_filename(filename)}"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "wb") as handle:
        handle.write(content)
    return os.path.basename(filename), path


def create_feedback(
    db: Session,
    *,
    name: str,
    rating: int,
    feedback_type: str,
    comment: str,
    contact_gmail: bool = False,
    contact_phone: bool = False,
    query_id: int | None = None,
    attachment_name: str | None = None,
    attachment_path: str | None = None,
) -> Feedback:
    fields = validate_submission(
        name=name,
        rating=rating,
        feedback_type=feedback_type,
        comment=comment,
    )
    if query_id is not None and db.get(SearchQuery, query_id) is None:
        raise FeedbackError("ไม่พบคำถามที่อ้างอิง", 404)

    row = Feedback(
        submitter_name=fields["submitter_name"],
        contact_gmail=bool(contact_gmail),
        contact_phone=bool(contact_phone),
        rating=fields["rating"],
        feedback_type=fields["feedback_type"],
        comment=fields["comment"],
        query_id=query_id,
        attachment_name=attachment_name,
        attachment_path=attachment_path,
        status="Open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_feedbacks(
    db: Session,
    *,
    feedback_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> list[Feedback]:
    query = db.query(Feedback)
    if feedback_type and feedback_type != "All":
        if feedback_type not in ALLOWED_TYPES:
            raise FeedbackError("ประเภทไม่ถูกต้อง")
        query = query.filter(Feedback.feedback_type == feedback_type)
    if status and status != "All":
        if status not in ALLOWED_STATUSES:
            raise FeedbackError("สถานะไม่ถูกต้อง")
        query = query.filter(Feedback.status == status)
    keyword = (q or "").strip()
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Feedback.comment.ilike(like),
                Feedback.submitter_name.ilike(like),
                Feedback.attachment_name.ilike(like),
            )
        )
    return query.order_by(Feedback.created_at.desc(), Feedback.id.desc()).all()


def update_feedback_status(db: Session, feedback_id: int, status: str) -> Feedback:
    if status not in ALLOWED_STATUSES:
        raise FeedbackError("สถานะไม่ถูกต้อง")
    row = db.get(Feedback, feedback_id)
    if row is None:
        raise FeedbackError("ไม่พบรายการ Feedback", 404)
    row.status = status
    db.commit()
    db.refresh(row)
    return row


def get_feedback_file(db: Session, feedback_id: int) -> tuple[Feedback, str]:
    row = db.get(Feedback, feedback_id)
    if row is None or not row.attachment_path:
        raise FeedbackError("ไม่พบไฟล์แนบ", 404)
    if not os.path.isfile(row.attachment_path):
        raise FeedbackError("ไม่พบไฟล์แนบบนดิสก์", 404)
    return row, row.attachment_path
