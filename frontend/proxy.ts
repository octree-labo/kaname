import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * ログイン状態の簡易チェックのみを行う（UX目的のショートカット）。
 * セッションCookieの署名検証はできないため、実際の認可判定は必ず
 * バックエンドAPI（401応答）で行われる。ここでの判定は「体験のための先回り」に過ぎない。
 */
const SESSION_COOKIE_NAME =
  process.env.NEXT_PUBLIC_SESSION_COOKIE_NAME ?? "kaname_session";

export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE_NAME);

  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!login|_next/static|_next/image|favicon.ico).*)",
  ],
};
