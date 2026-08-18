"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { QuotationOut } from "@/lib/types";
import { formatApprovalStatus } from "@/lib/format";
import { DataTable, type Column } from "@/components/DataTable";
import { PartnerPicker } from "@/components/PartnerPicker";

const APPROVAL_STATUS_OPTIONS = [
  { value: "", label: "すべて" },
  { value: "draft", label: "未承認" },
  { value: "pending", label: "承認待ち" },
  { value: "approved", label: "承認済み" },
  { value: "rejected", label: "却下" },
];

export default function QuotationsPage() {
  const [partnerId, setPartnerId] = useState("");
  const [keyword, setKeyword] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [approvalStatus, setApprovalStatus] = useState("");

  const params = new URLSearchParams();
  if (partnerId) params.set("partner_id", partnerId);
  if (keyword) params.set("keyword", keyword);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (approvalStatus) params.set("approval_status", approvalStatus);
  const query = params.toString();

  const { data } = useSWR<QuotationOut[]>(`/api/quotations${query ? `?${query}` : ""}`, fetcher);

  const columns: Column<QuotationOut>[] = [
    { key: "quotationNo", label: "見積番号", sortable: true },
    {
      key: "partnerName",
      label: "取引先",
      sortable: true,
      render: (r) => (r.partnerCode ? `${r.partnerCode} ${r.partnerName ?? ""}` : r.partnerId),
    },
    { key: "quotationDate", label: "見積日", sortable: true },
    { key: "expiryDate", label: "見積期限", sortable: true, render: (r) => r.expiryDate ?? "-" },
    {
      key: "approvalStatus",
      label: "承認状態",
      sortable: true,
      render: (r) => formatApprovalStatus(r.approvalStatus),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">見積</h1>
        <Link
          href="/quotations/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          新規作成
        </Link>
      </div>

      <div className="mt-4 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-5">
        <div>
          <label className="block text-xs text-slate-600">取引先</label>
          <PartnerPicker value={partnerId} onChange={setPartnerId} placeholder="取引先で絞込み" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">見積番号</label>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="部分一致" className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">見積日（開始）</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">見積日（終了）</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">承認状態</label>
          <select value={approvalStatus} onChange={(e) => setApprovalStatus(e.target.value)} className="w-full">
            {APPROVAL_STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 min-h-0 flex-1">
        <DataTable columns={columns} rows={data ?? []} rowHref={(row) => `/quotations/${row.id}`} />
      </div>
    </div>
  );
}
