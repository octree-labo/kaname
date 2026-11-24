/**
 * バックエンドAPI（FastAPI, kaname.ajesta.work とは別サブドメイン想定）を
 * 呼び出す薄いクライアント。認証はセッションCookie（.ajesta.work ドメイン）に
 * 委ねるため、常に credentials: "include" を付与する。
 *
 * 実際の認証チェックはバックエンドが行う（401を返す）。ここではその401を
 * 検知してログイン画面に遷移させるだけで、フロント側では認可判定を行わない。
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (res.status === 401) {
    // /auth/me は未ログイン・ゲストでも呼ばれ、401は「未ログイン」という正常な
    // 状態を表すだけなので、ここでは強制リダイレクトしない（呼び出し元の
    // useCurrentUser が user=undefined として扱う）。ルートレイアウトの
    // AdSenseGuest も含め全ページでこれを呼ぶため、ここで無条件にリダイレクト
    // すると /login 自身で 401→リダイレクト→再マウント→401… の無限リロード
    // ループになる。
    if (path !== "/auth/me" && typeof window !== "undefined") {
      // Reactコンポーネント外(fetchラッパー)から呼ばれるため useRouter は使えない。
      // 意図的にハードリダイレクトしてクライアント状態を確実にリセットする。
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
    throw new ApiError(401, "authentication required");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
};

/** SWR用フェッチャー */
export const fetcher = <T>(path: string) => api.get<T>(path);

export function pdfUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
