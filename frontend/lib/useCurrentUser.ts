import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";

/** ログイン中のユーザー（ゲスト含む）を返す共通フック。 */
export function useCurrentUser() {
  const { data: user, isLoading } = useSWR<CurrentUser>("/auth/me", fetcher, {
    shouldRetryOnError: false,
  });
  return {
    user,
    isLoading,
    isGuest: user?.role === "guest",
    canWrite: !!user && user.role !== "guest",
  };
}
