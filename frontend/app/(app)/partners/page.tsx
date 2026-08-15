"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";
import type { PartnerWithCurrentDetailOut } from "@/lib/types";
import { DataTable, type Column } from "@/components/DataTable";

const PARTNER_TYPE_LABEL: Record<string, string> = {
  customer: "得意先",
  supplier: "仕入先",
  both: "得意先/仕入先",
};

export default function PartnersPage() {
  const [keyword, setKeyword] = useState("");
  const { data } = useSWR<PartnerWithCurrentDetailOut[]>(
    `/api/partners${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`,
    fetcher
  );

  const columns: Column<PartnerWithCurrentDetailOut>[] = [
    { key: "partnerCode", label: "取引先コード", sortable: true },
    {
      key: "name",
      label: "会社名",
      sortable: true,
      sortValue: (row) => row.currentDetail?.name ?? "",
      render: (row) => row.currentDetail?.name ?? "(未設定)",
    },
    {
      key: "partnerType",
      label: "区分",
      sortable: true,
      render: (row) => PARTNER_TYPE_LABEL[row.partnerType],
    },
    {
      key: "isActive",
      label: "状態",
      sortable: true,
      render: (row) => (row.isActive ? "有効" : "無効"),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">取引先</h1>
        <Link
          href="/partners/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          新規登録
        </Link>
      </div>

      <input
        aria-label="会社名・コードで検索"
        placeholder="会社名・コードで検索"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        className="mt-4 w-72 shrink-0"
      />

      <div className="mt-4 min-h-0 flex-1">
        <DataTable columns={columns} rows={data ?? []} rowHref={(row) => `/partners/${row.id}`} />
      </div>
    </div>
  );
}
