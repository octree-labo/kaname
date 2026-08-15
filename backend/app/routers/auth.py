"""ログイン/ログアウト。https://games.ajesta.work/admin/dashboard と同じ導線
（未ログイン→ログイン画面→「Googleでログイン」→ /auth/login/google ）を踏襲する。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..schemas import CurrentUser
from ..security import get_current_user, get_or_create_user, is_email_allowed, oauth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=oauth_failed")

    email = userinfo["email"].lower()
    if not userinfo.get("email_verified", True):
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=email_not_verified")

    if not is_email_allowed(email):
        # 未許可ユーザーはユーザーテーブルに登録せず、そのまま拒否する。
        return RedirectResponse(url=f"{settings.frontend_origin}/login?error=access_denied")

    user = get_or_create_user(db, email=email, name=userinfo.get("name"))
    request.session["user_email"] = user.email
    request.session["user_name"] = user.name
    return RedirectResponse(url=settings.frontend_origin)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=CurrentUser)
async def me(user=Depends(get_current_user)):
    return CurrentUser(email=user.email, name=user.name)
