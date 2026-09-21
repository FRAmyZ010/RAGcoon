from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_administrator
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    ROLE_ADMINISTRATOR,
    create_access_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.username == body.username)
        .first()
    )
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        )

    role_name = user.role.name if user.role else None
    if role_name != ROLE_ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sprint 2 รองรับเฉพาะ Administrator",
        )

    token = create_access_token(
        data={"sub": user.username, "role": role_name},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    return Token(
        access_token=token,
        token_type="bearer",
        role=role_name,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_administrator)):
    return current_user
