"""Google OAuth ログインとセッションによるアクセス制御。

- kaname.ajesta.work を使えるのは ALLOWED_EMAILS に含まれるメールアドレスのみ。
- ログイン状態は署名付きセッションCookie（starlette.SessionMiddleware）で保持する。
- /auth/* 以外の API ルーターは get_current_user 依存関係で保護する。
"""
from __future__ import annotations

from dataclasses import dataclass

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    client_kwargs={"scope": "openid email profile"},
)


@dataclass
class SessionUser:
    id: int
    email: str
    name: str | None


def is_email_allowed(email: str) -> bool:
    return email.strip().lower() in settings.allowed_emails


def get_or_create_user(db: Session, *, email: str, name: str | None) -> models.User:
    email = email.strip().lower()
    user = db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()
    if user is not None:
        if name and user.name != name:
            user.name = name
            db.commit()
        return user

    employee_code = email.split("@")[0]
    user = models.User(employee_code=employee_code, name=name or email, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> SessionUser:
    email = request.session.get("user_email")
    if not email or not is_email_allowed(email):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    user = db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()
    if user is None:
        # 許可済みだが users テーブルに未登録（初回コールバック前に手動でCookieを持ち込んだ等）
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    return SessionUser(id=user.id, email=user.email, name=user.name)
