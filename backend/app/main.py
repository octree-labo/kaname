from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .routers import admin, auth, documents, inventory, masters

app = FastAPI(title="基幹業務システム API", version="0.1.0")

# セッションCookie。kaname.ajesta.work（フロント）と別サブドメインでAPIを
# 運用する場合は COOKIE_DOMAIN に上位ドメイン（例: .ajesta.work）を設定する。
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.cookie_secure,
    domain=settings.cookie_domain,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 認証まわり（ログイン導線）は公開。それ以外の /api/* は全て要ログイン。
app.include_router(auth.router)
app.include_router(masters.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
