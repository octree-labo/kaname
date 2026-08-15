"use client";

import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { formatDocumentStatus } from "@/lib/format";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import { DataTable, type Column } from "@/components/DataTable";

interface DocHeader {
  id: number;
  partnerId: number;
  status?: string;
  [key: string]: unknown;
}

export function DocumentListPage({ config }: { config: DocumentModuleConfig }) {
  const { data } = useSWR<DocHeader[]>(config.apiPath, fetcher);

  const columns: Column<DocHeader>[] = [
    { key: config.noField, label: config.noLabel },
    { key: "partnerId", label: "取引先ID" },
    { key: config.dateField, label: config.dateLabel },
  ];
  if (config.hasStatus) {
    columns.push({
      key: "status",
      label: "状態",
      render: (row) => formatDocumentStatus(String(row.status ?? "")),
    });
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">{config.label}</h1>
        <Link
          href={`/${config.key}/new`}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          新規作成
        </Link>
      </div>

      <div className="mt-4">
        <DataTable columns={columns} rows={data ?? []} rowHref={(row) => `/${config.key}/${row.id}`} />
      </div>
    </div>
  );
}
