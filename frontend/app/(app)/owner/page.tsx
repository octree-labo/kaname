"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { AdminUserOut } from "@/lib/types";

const ROLE_LABEL: Record<string, string> = { owner: "オーナー", member: "利用者" };
const STATUS_LABEL: Record<string, string> = { pending: "申請中", approved: "承認済み", rejected: "却下" };
const STATUS_BADGE: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-slate-100 text-slate-600 border-slate-200",
};

export default function OwnerPage() {
  const { data: users, error, mutate } = useSWR<AdminUserOut[]>("/api/admin/users", fetcher, {
    shouldRetryOnError: false,
  });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error instanceof ApiError && error.status === 403) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        オーナー権限が必要です。
      </div>
    );
  }
  if (!users) return <p className="text-sm text-slate-600">読み込み中...</p>;

  async function handleAction(id: number, action: "approve" | "reject") {
    setActionError(null);
    setBusyId(id);
    try {
      await api.post(`/api/admin/users/${id}/${action}`);
      mutate();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "操作に失敗しました");
    } finally {
      setBusyId(null);
    }
  }

  const pending = users.filter((u) => u.status === "pending");
  const others = users.filter((u) => u.status !== "pending");

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">オーナーメニュー</h1>
        <p className="mt-1 text-sm text-slate-600">アカウント申請の承認・却下を行います。</p>
      </div>

      {actionError && <p className="text-sm text-red-600">{actionError}</p>}

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">申請中のアカウント（{pending.length}件）</h2>
        {pending.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">申請はありません。</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                  <th className="px-3 py-2">名前</th>
                  <th className="px-3 py-2">メールアドレス</th>
                  <th className="px-3 py-2">申請日時</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2">{u.name}</td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2 text-slate-600">{u.createdAt.slice(0, 16).replace("T", " ")}</td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button
                          disabled={busyId === u.id}
                          onClick={() => handleAction(u.id, "approve")}
                          className="rounded-md bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                        >
                          利用者として承認
                        </button>
                        <button
                          disabled={busyId === u.id}
                          onClick={() => handleAction(u.id, "reject")}
                          className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                        >
                          却下
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">登録済みアカウント</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">名前</th>
                <th className="px-3 py-2">メールアドレス</th>
                <th className="px-3 py-2">権限</th>
                <th className="px-3 py-2">状態</th>
              </tr>
            </thead>
            <tbody>
              {others.map((u) => (
                <tr key={u.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{u.name}</td>
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2">{ROLE_LABEL[u.role]}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${STATUS_BADGE[u.status]}`}>
                      {STATUS_LABEL[u.status]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
