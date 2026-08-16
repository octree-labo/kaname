"""Google OAuth ログインとセッションによるアクセス制御。

- ログインできるのは users.status = 'approved' のアカウントのみ。
- 新規ユーザーは「アカウント申請」(/auth/apply/google) で status='pending' として登録され、
  オーナーが承認するまでログインできない。
- OWNER_EMAILS に含まれるメールアドレスは、初回ログイン時に自動的に
  role='owner', status='approved' で登録される（オーナーの立ち上げ用ブートストラップ）。
- ログイン状態は署名付きセッションCookie（starlette.SessionMiddleware）で保持する。
- /auth/* 以外の API ルーターは get_current_user（オーナー限定は get_current_owner）で保護する。
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


GUEST_ROLE = "guest"


@dataclass
class SessionUser:
    id: int | None
    email: str | None
    name: str | None
    role: str


def is_owner_bootstrap_email(email: str) -> bool:
    return email.strip().lower() in settings.owner_emails


def get_user_by_email(db: Session, email: str) -> models.User | None:
    email = email.strip().lower()
    return db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()


def provision_login_user(db: Session, *, email: str, name: str | None) -> models.User | None:
    """ログイン試行時のユーザー解決。

    未登録かつオーナーブートストラップ対象のメールアドレスであれば、
    その場でオーナーとして自動登録する。それ以外の未登録メールアドレスは
    None を返す（＝アカウント申請が必要）。
    """
    email = email.strip().lower()
    user = get_user_by_email(db, email)
    if user is not None:
        if name and user.name != name:
            user.name = name
            db.commit()
        return user

    if not is_owner_bootstrap_email(email):
        return None

    employee_code = email.split("@")[0]
    user = models.User(
        employee_code=employee_code,
        name=name or email,
        email=email,
        role=models.UserRole.owner,
        status=models.UserStatus.approved,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_pending_application(db: Session, *, email: str, name: str | None) -> models.User:
    """アカウント申請の登録。既存ユーザーがいればそれをそのまま返す。"""
    email = email.strip().lower()
    user = get_user_by_email(db, email)
    if user is not None:
        return user

    employee_code = email.split("@")[0]
    user = models.User(
        employee_code=employee_code,
        name=name or email,
        email=email,
        role=models.UserRole.member,
        status=models.UserStatus.pending,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> SessionUser:
    email = request.session.get("user_email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    user = get_user_by_email(db, email)
    if user is None or user.status != models.UserStatus.approved:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")

    return SessionUser(id=user.id, email=user.email, name=user.name, role=user.role)


def get_current_owner(user: SessionUser = Depends(get_current_user)) -> SessionUser:
    if user.role != models.UserRole.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner only")
    return user


def get_viewer(request: Request, db: Session = Depends(get_db)) -> SessionUser:
    """閲覧用の依存関係。ログイン済みユーザーに加え、ゲスト（表示専用）も許可する。

    書き込み系エンドポイントは引き続き get_current_user / get_current_owner を使うこと。
    """
    email = request.session.get("user_email")
    if email:
        user = get_user_by_email(db, email)
        if user is not None and user.status == models.UserStatus.approved:
            return SessionUser(id=user.id, email=user.email, name=user.name, role=user.role)

    if request.session.get("guest"):
        return SessionUser(id=None, email=None, name="ゲスト", role=GUEST_ROLE)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
