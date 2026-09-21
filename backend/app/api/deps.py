from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import (
    ROLE_ADMINISTRATOR,
    decode_access_token,
    is_token_invalid,
)
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ต้องเข้าสู่ระบบก่อน",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        if is_token_invalid(exc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token ไม่ถูกต้องหรือหมดอายุ",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.username == username)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ไม่พบผู้ใช้ในระบบ",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_administrator(
    current_user: User = Depends(get_current_user),
) -> User:
    role_name = current_user.role.name if current_user.role else None
    if role_name != ROLE_ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ต้องเป็น Administrator เท่านั้น",
        )
    return current_user
