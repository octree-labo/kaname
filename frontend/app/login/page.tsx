"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: "このアカウントには利用権限がありません。管理者にご確認ください。",
  oauth_failed: "Google認証に失敗しました。もう一度お試しください。",
  email_not_verified: "メールアドレスが確認されていません。",
  not_registered: "このアカウントは未登録です。「アカウント申請」からお申し込みください。",
  pending_approval: "アカウント申請を受け付けています。オーナーの承認をお待ちください。",
  already_registered: "このアカウントは既に登録済みです。「Googleでログイン」をご利用ください。",
};

const APPLIED_MESSAGES: Record<string, string> = {
  "1": "アカウント申請を受け付けました。オーナーの承認までお待ちください。",
  already_pending: "既に申請済みです。オーナーの承認をお待ちください。",
};

function LoginNotice() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");
  const applied = searchParams.get("applied");

  if (error) {
    return (
      <p className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
        {ERROR_MESSAGES[error] ?? "ログインに失敗しました。"}
      </p>
    );
  }
  if (applied) {
    return (
      <p className="mt-4 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-700 border border-blue-200">
        {APPLIED_MESSAGES[applied] ?? "申請を受け付けました。"}
      </p>
    );
  }
  return null;
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-slate-900">
          管理者ログイン — 基幹業務システム
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          kaname.ajesta.work は許可されたアカウントのみ利用できます。
        </p>

        <a
          href={`${API_BASE_URL}/auth/login/google`}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Googleでログイン
        </a>

        <a
          href={`${API_BASE_URL}/auth/apply/google`}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          🆕 アカウント申請
        </a>

        <Suspense fallback={null}>
          <LoginNotice />
        </Suspense>
      </div>
    </div>
  );
}
