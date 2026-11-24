import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * ログイン状態の簡易チェックのみを行う（UX目的のショートカット）。
 * セッションCookieの署名検証はできないため、実際の認可判定は必ず
 * バックエンドAPI（401応答）で行われる。ここでの判定は「体験のための先回り」に過ぎない。
 *
 * 2026-11-24: 以前はCookieが無い訪問者を無条件に/loginへ飛ばしていたが、
 * 「kaname.ajesta.work/ に接続したらそのまま読み取り専用で見られるように
 * したい」との要望を受け、代わりにバックエンドの /auth/guest を
 * サーバー間で呼び、その場でゲスト(読み取り専用)セッションを自動的に
 * 確立してから元のページをそのまま表示するようにした。/loginへの遷移は
 * 「ゲスト終了」ボタン(app/(app)/layout.tsx のhandleLogout)を押した時
 * だけ起きる。
 */
const SESSION_COOKIE_NAME =
  process.env.NEXT_PUBLIC_SESSION_COOKIE_NAME ?? "kaname_session";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(SESSION_COOKIE_NAME);

  if (!hasSession) {
    try {
      // /auth/guest 自体はリダイレクトを返すだけのエンドポイントで、
      // 欲しいのはそのレスポンスが載せてくるSet-Cookie(ゲストセッション)
      // だけなので、リダイレクト先には追従しない。
      const guestRes = await fetch(`${API_BASE_URL}/auth/guest`, {
        redirect: "manual",
      });
      const setCookie = guestRes.headers.get("set-cookie");
      if (setCookie) {
        const response = NextResponse.next();
        // バックエンド(FastAPI/Starlette SessionMiddleware)が発行した
        // Set-Cookieの文字列(Domain/Secure/SameSite等の属性込み)をそのまま
        // 転送する。属性をここで組み直さないことで、バックエンド側の
        // Cookie設定(app/config.py)が変わってもここを追従修正する必要がない。
        response.headers.set("set-cookie", setCookie);
        return response;
      }
    } catch {
      // バックエンドに到達できない場合のみ、従来通りログイン画面へ
      // フォールバックする。
    }
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!login|privacy|ads.txt|_next/static|_next/image|favicon.ico).*)",
  ],
};
