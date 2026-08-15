"""ログイン/アカウント申請/ログアウト。

https://games.ajesta.work/admin/dashboard と同じ導線
（未ログイン→ログイン画面→「Googleでログイン」/「アカウント申請」）を踏襲する。
どちらも同じ Google OAuth コールバック(/auth/google/callback)を使い、
リダイレクト前にセッションへ保存した oauth_intent で処理を振り分ける。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import UserStatus
from ..schemas import CurrentUser
from ..security import (
    create_pending_application,
    get_current_user,
    get_user_by_email,
    oauth,
    provision_login_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/google")
async def login_google(request: Request):
    request.session["oauth_intent"] = "login"
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/apply/google")
async def apply_google(request: Request):
    request.session["oauth_intent"] = "apply"
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    intent = request.session.pop("oauth_intent", "login")

    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=oauth_failed")

    email = userinfo["email"].lower()
    if not userinfo.get("email_verified", True):
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=email_not_verified")

    name = userinfo.get("name")

    if intent == "apply":
        existing = get_user_by_email(db, email)
        if existing is not None:
            if existing.status == UserStatus.approved:
                return RedirectResponse(url=f"{settings.frontend_origin}/login?error=already_registered")
            return RedirectResponse(url=f"{settings.frontend_origin}/login?applied=already_pending")
        create_pending_application(db, email=email, name=name)
        return RedirectResponse(url=f"{settings.frontend_origin}/login?applied=1")

    user = provision_login_user(db, email=email, name=name)
    if user is None:
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=not_registered")
    if user.status == UserStatus.pending:
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=pending_approval")
    if user.status == UserStatus.rejected:
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=access_denied")

    request.session["user_email"] = user.email
    request.session["user_name"] = user.name
    return RedirectResponse(url=settings.frontend_origin)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=CurrentUser)
async def me(user=Depends(get_current_user)):
    return CurrentUser(email=user.email, name=user.name, role=user.role)
