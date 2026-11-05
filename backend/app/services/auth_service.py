from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ROLE_ADMINISTRATOR, ROLE_AI_ENGINEER, get_password_hash
from app.models.role import Role
from app.models.user import User


def ensure_administrator_seed(db: Session) -> User | None:
    """
    Ensure Administrator role exists and seed the Admin user from env
    when that username is not present yet. Does not reset an existing password.
    """
    role = db.query(Role).filter(Role.name == ROLE_ADMINISTRATOR).first()
    if role is None:
        role = Role(
            name=ROLE_ADMINISTRATOR,
            description="Manages document archive and admin operations",
        )
        db.add(role)
        db.commit()
        db.refresh(role)

    existing = (
        db.query(User)
        .filter(User.username == settings.ADMIN_USERNAME)
        .first()
    )
    if existing is not None:
        # Older seeds used *.local which breaks EmailStr-based clients; keep in sync with env.
        if existing.email != settings.ADMIN_EMAIL:
            existing.email = settings.ADMIN_EMAIL
            db.commit()
            db.refresh(existing)
        return existing

    admin = User(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
        role_id=role.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def ensure_ai_engineer_seed(db: Session) -> User | None:
    """
    Ensure AI Engineer role exists and seed that user from env when missing.
    Does not reset an existing password.
    """
    role = db.query(Role).filter(Role.name == ROLE_AI_ENGINEER).first()
    if role is None:
        role = Role(
            name=ROLE_AI_ENGINEER,
            description="Manages AI configuration and retrieval presets",
        )
        db.add(role)
        db.commit()
        db.refresh(role)

    existing = (
        db.query(User)
        .filter(User.username == settings.AI_ENGINEER_USERNAME)
        .first()
    )
    if existing is not None:
        if existing.email != settings.AI_ENGINEER_EMAIL:
            existing.email = settings.AI_ENGINEER_EMAIL
            db.commit()
            db.refresh(existing)
        if existing.role_id != role.id:
            existing.role_id = role.id
            db.commit()
            db.refresh(existing)
        return existing

    engineer = User(
        username=settings.AI_ENGINEER_USERNAME,
        email=settings.AI_ENGINEER_EMAIL,
        hashed_password=get_password_hash(settings.AI_ENGINEER_PASSWORD),
        role_id=role.id,
    )
    db.add(engineer)
    db.commit()
    db.refresh(engineer)
    return engineer
