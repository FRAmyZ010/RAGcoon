import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_administrator
from app.core.database import get_db
from app.models.user import User
from app.schemas.feedback import FeedbackResponse, FeedbackStatusUpdate
from app.services.feedback_service import (
    FeedbackError,
    create_feedback,
    get_feedback_file,
    list_feedbacks,
    save_attachment,
    update_feedback_status,
    validate_submission,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def _raise_http(exc: FeedbackError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    name: str = Form(...),
    rating: int = Form(...),
    feedback_type: str = Form(...),
    comment: str = Form(...),
    contact_gmail: bool = Form(False),
    contact_phone: bool = Form(False),
    query_id: int | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    attachment_name = None
    attachment_path = None
    try:
        validate_submission(
            name=name,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
        )
        if file is not None and file.filename:
            content = await file.read()
            attachment_name, attachment_path = save_attachment(file.filename, content)
        return create_feedback(
            db,
            name=name,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
            contact_gmail=contact_gmail,
            contact_phone=contact_phone,
            query_id=query_id,
            attachment_name=attachment_name,
            attachment_path=attachment_path,
        )
    except FeedbackError as exc:
        if attachment_path and os.path.isfile(attachment_path):
            os.remove(attachment_path)
        _raise_http(exc)


@router.get("", response_model=list[FeedbackResponse])
def read_feedback(
    feedback_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_administrator),
):
    try:
        return list_feedbacks(db, feedback_type=feedback_type, status=status, q=q)
    except FeedbackError as exc:
        _raise_http(exc)


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
def patch_feedback_status(
    feedback_id: int,
    body: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_administrator),
):
    try:
        return update_feedback_status(db, feedback_id, body.status)
    except FeedbackError as exc:
        _raise_http(exc)


@router.get("/{feedback_id}/file")
def download_feedback_file(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_administrator),
):
    try:
        row, path = get_feedback_file(db, feedback_id)
    except FeedbackError as exc:
        _raise_http(exc)
    return FileResponse(path, filename=row.attachment_name or "attachment")
