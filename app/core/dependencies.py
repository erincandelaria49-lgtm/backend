from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User, AdminAccount


def get_current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "", 1)
    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_issuer)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    try:
        user_id_int = int(str(user_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id_int).one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    user.last_seen = func.now()
    db.commit()
    return user


def get_current_admin(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "", 1)
    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_issuer)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    role = payload.get("role")
    if role in {"admin", "faculty"}:
        subject = payload.get("sub") or ""
        try:
            admin_id = int(subject.replace("admin:", "", 1)) if subject.startswith("admin:") else None
        except (TypeError, ValueError):
            admin_id = None
        if admin_id is None:
            raise HTTPException(status_code=401, detail="Invalid staff token")
        admin = db.query(AdminAccount).filter(AdminAccount.id == admin_id).one_or_none()
        if not admin or admin.role not in {"admin", "faculty"}:
            raise HTTPException(status_code=401, detail="Invalid staff token")
        return admin

    user_id = payload.get("sub")
    try:
        user_id_int = int(str(user_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id_int).one_or_none()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
