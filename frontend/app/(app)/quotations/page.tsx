"use client";

import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { QuotationOut } from "@/lib/types";
import { formatApprovalStatus } from "@/lib/format";
import { DataTable, type Column } from "@/components/DataTable";

export default function QuotationsPage() {
  const { data } = useSWR<QuotationOut[]>("/api/quotations", fetcher);

  const columns: Column<QuotationOut>[] = [
    { key: "quotationNo", label: "見積番号" },
    { key: "partnerId", label: "取引先ID" },
    { key: "quotationDate", label: "見積日" },
    { key: "expiryDate", label: "見積期限", render: (r) => r.expiryDate ?? "-" },
    {
      key: "approvalStatus",
      label: "承認状態",
      render: (r) => formatApprovalStatus(r.approvalStatus),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">見積</h1>
        <Link
          href="/quotations/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          新規作成
        </Link>
      </div>

      <div className="mt-4">
        <DataTable columns={columns} rows={data ?? []} rowHref={(row) => `/quotations/${row.id}`} />
      </div>
    </div>
  );
}
