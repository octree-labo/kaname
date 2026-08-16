"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { formatDocumentStatus } from "@/lib/format";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import { DataTable, type Column } from "@/components/DataTable";
import { PartnerPicker } from "@/components/PartnerPicker";
import { useCurrentUser } from "@/lib/useCurrentUser";

interface DocHeader {
  id: number;
  partnerId: number;
  partnerCode?: string | null;
  partnerName?: string | null;
  status?: string;
  [key: string]: unknown;
}

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "すべて" },
  { value: "draft", label: "下書き" },
  { value: "confirmed", label: "確定" },
  { value: "cancelled", label: "取消" },
];

const APPROVAL_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "すべて" },
  { value: "draft", label: "未承認" },
  { value: "pending", label: "承認待ち" },
  { value: "approved", label: "承認済み" },
  { value: "rejected", label: "却下" },
];

export function DocumentListPage({ config }: { config: DocumentModuleConfig }) {
  const { canWrite } = useCurrentUser();
  const [partnerId, setPartnerId] = useState("");
  const [keyword, setKeyword] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState("");

  const statusParamName = config.key === "quotations" ? "approval_status" : "status";
  const params = new URLSearchParams();
  if (partnerId) params.set("partner_id", partnerId);
  if (keyword) params.set("keyword", keyword);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (status) params.set(statusParamName, status);
  const query = params.toString();

  const { data } = useSWR<DocHeader[]>(`${config.apiPath}${query ? `?${query}` : ""}`, fetcher);

  const columns: Column<DocHeader>[] = [
    { key: config.noField, label: config.noLabel, sortable: true },
    {
      key: "partnerName",
      label: "取引先",
      sortable: true,
      render: (row) => (row.partnerCode ? `${row.partnerCode} ${row.partnerName ?? ""}` : String(row.partnerId)),
    },
    { key: config.dateField, label: config.dateLabel, sortable: true },
  ];
  const statusOptions = config.key === "quotations" ? APPROVAL_STATUS_OPTIONS : STATUS_OPTIONS;
  if (config.hasStatus) {
    columns.push({
      key: "status",
      label: "状態",
      sortable: true,
      render: (row) => formatDocumentStatus(String(row.status ?? "")),
    });
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">{config.label}</h1>
        {canWrite && (
          <Link
            href={`/${config.key}/new`}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            新規作成
          </Link>
        )}
      </div>

      <div className="mt-4 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-5">
        <div>
          <label className="block text-xs text-slate-600">取引先</label>
          <PartnerPicker value={partnerId} onChange={setPartnerId} placeholder="取引先で絞込み" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">{config.noLabel}</label>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="部分一致" className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">{config.dateLabel}（開始）</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-full" />
        </div>
        <div>
          <label className="block text-xs text-slate-600">{config.dateLabel}（終了）</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-full" />
        </div>
        {config.hasStatus && (
          <div>
            <label className="block text-xs text-slate-600">状態</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full">
              {statusOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="mt-4 min-h-0 flex-1">
        <DataTable columns={columns} rows={data ?? []} rowHref={(row) => `/${config.key}/${row.id}`} />
      </div>
    </div>
  );
}
