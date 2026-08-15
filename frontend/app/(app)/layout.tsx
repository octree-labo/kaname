"use client";

import useSWR from "swr";
import { useRouter } from "next/navigation";
import { fetcher, api } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";
import { Nav } from "@/components/Nav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, error, isLoading } = useSWR<CurrentUser>("/auth/me", fetcher, {
    shouldRetryOnError: false,
  });

  async function handleLogout() {
    await api.post("/auth/logout");
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen">
      <Nav />
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-4 border-b border-slate-200 bg-white px-6">
          {isLoading && <span className="text-sm text-slate-600">読み込み中...</span>}
          {!isLoading && !error && user && (
            <>
              <span className="text-sm text-slate-700">
                {user.name ?? user.email}
              </span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-100"
              >
                ログアウト
              </button>
            </>
          )}
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
