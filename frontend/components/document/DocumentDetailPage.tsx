"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { formatDocumentStatus, formatNumber } from "@/lib/format";
import type { DocumentModuleConfig } from "@/lib/documentModules";

interface DocLine {
  id: number;
  lineNo: number;
  productId?: number;
  productCode?: string | null;
  productName?: string | null;
  quantity?: string;
  unitPrice?: string;
  amount: string;
  [key: string]: unknown;
}

interface DocDetail {
  id: number;
  partnerId: number;
  partnerCode?: string | null;
  partnerName?: string | null;
  status?: string;
  lines: DocLine[];
  [key: string]: unknown;
}

export function DocumentDetailPage({ config }: { config: DocumentModuleConfig }) {
  const params = useParams<{ id: string }>();
  const { data } = useSWR<DocDetail>(`${config.apiPath}/${params.id}`, fetcher);

  if (!data) return <p className="text-sm text-slate-600">読み込み中...</p>;

  const total = data.lines.reduce((sum, l) => sum + Number(l.amount), 0);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">
          {config.label} {String(data[config.noField] ?? "")}
        </h1>
        <Link
          href={`/${config.key}/${data.id}/edit`}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
        >
          編集
        </Link>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <dt className="text-slate-600">取引先</dt>
        <dd>{data.partnerCode ? `${data.partnerCode} ${data.partnerName ?? ""}` : data.partnerId}</dd>
        <dt className="text-slate-600">{config.dateLabel}</dt>
        <dd>{String(data[config.dateField] ?? "-")}</dd>
        {config.hasStatus && (
          <>
            <dt className="text-slate-600">状態</dt>
            <dd>{formatDocumentStatus(String(data.status ?? ""))}</dd>
          </>
        )}
      </dl>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">明細</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">No</th>
                {config.lineKind === "product" && (
                  <>
                    <th className="px-3 py-2">商品コード</th>
                    <th className="px-3 py-2">商品名</th>
                    <th className="px-3 py-2 text-right">数量</th>
                    <th className="px-3 py-2 text-right">単価</th>
                  </>
                )}
                {config.upstreamLineField && <th className="px-3 py-2">上位明細ID</th>}
                <th className="px-3 py-2 text-right">金額</th>
              </tr>
            </thead>
            <tbody>
              {data.lines.map((line) => (
                <tr key={line.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{line.lineNo}</td>
                  {config.lineKind === "product" && (
                    <>
                      <td className="px-3 py-2">{line.productCode ?? line.productId}</td>
                      <td className="px-3 py-2">{line.productName ?? "-"}</td>
                      <td className="px-3 py-2 text-right">{formatNumber(line.quantity)}</td>
                      <td className="px-3 py-2 text-right">{formatNumber(line.unitPrice)}</td>
                    </>
                  )}
                  {config.upstreamLineField && (
                    <td className="px-3 py-2 text-slate-600">
                      {line[config.upstreamLineField] != null ? String(line[config.upstreamLineField]) : "(直接入力)"}
                    </td>
                  )}
                  <td className="px-3 py-2 text-right">{formatNumber(line.amount)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={100} className="px-3 py-2 text-right text-sm font-medium text-slate-700">
                  合計: {formatNumber(total)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>
    </div>
  );
}
