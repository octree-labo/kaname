"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher, pdfUrl } from "@/lib/api";
import type { QuotationOut, QuotationLineWithRemainingOut } from "@/lib/types";
import { formatApprovalStatus, formatNumber } from "@/lib/format";

export default function QuotationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const quotationId = params.id;

  const { data: quotation, mutate: mutateQuotation } = useSWR<QuotationOut>(
    `/api/quotations/${quotationId}`,
    fetcher
  );
  const { data: lines } = useSWR<QuotationLineWithRemainingOut[]>(
    `/api/quotations/${quotationId}/lines`,
    fetcher
  );

  const [selected, setSelected] = useState<Record<number, boolean>>({});
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!quotation || !lines) return <p className="text-sm text-slate-600">読み込み中...</p>;

  async function handleApprove() {
    setError(null);
    setBusy(true);
    try {
      await api.post(`/api/quotations/${quotationId}/approve`);
      mutateQuotation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "承認に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmWhole() {
    setError(null);
    setBusy(true);
    try {
      const order = await api.post<{ id: number }>(`/api/quotations/${quotationId}/confirm-orders`, {
        mode: "whole_document",
      });
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "受注確定に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmSelected() {
    setError(null);
    const lineSelections = (lines ?? [])
      .filter((l) => selected[l.id])
      .map((l) => ({
        quotationLineId: l.id,
        quantity: quantities[l.id] ? Number(quantities[l.id]) : undefined,
      }));
    if (lineSelections.length === 0) {
      setError("受注確定する明細を選択してください");
      return;
    }
    setBusy(true);
    try {
      const order = await api.post<{ id: number }>(`/api/quotations/${quotationId}/confirm-orders`, {
        mode: "selected_lines",
        lineSelections,
      });
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "受注確定に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  const isApproved = quotation.approvalStatus === "approved";

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">見積 {quotation.quotationNo}</h1>
          <p className="mt-1 text-sm text-slate-600">
            承認状態: {formatApprovalStatus(quotation.approvalStatus)}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={pdfUrl(`/api/quotations/${quotationId}/pdf`)}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
          >
            PDF表示
          </a>
          {!isApproved && (
            <button
              onClick={handleApprove}
              disabled={busy}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              承認する
            </button>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <dt className="text-slate-600">取引先ID</dt>
        <dd>{quotation.partnerId}</dd>
        <dt className="text-slate-600">見積日</dt>
        <dd>{quotation.quotationDate}</dd>
        <dt className="text-slate-600">見積期限</dt>
        <dd>{quotation.expiryDate ?? "-"}</dd>
        <dt className="text-slate-600">見積条件</dt>
        <dd>{quotation.conditionText ?? "-"}</dd>
      </dl>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">明細（見積残数）</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">選択</th>
                <th className="px-3 py-2">No</th>
                <th className="px-3 py-2">商品ID</th>
                <th className="px-3 py-2 text-right">見積数量</th>
                <th className="px-3 py-2 text-right">受注済数量</th>
                <th className="px-3 py-2 text-right">見積残数</th>
                <th className="px-3 py-2 text-right">単価</th>
                <th className="px-3 py-2 w-32">受注数量指定</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <tr key={line.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={!!selected[line.id]}
                      onChange={(e) => setSelected((prev) => ({ ...prev, [line.id]: e.target.checked }))}
                    />
                  </td>
                  <td className="px-3 py-2">{line.lineNo}</td>
                  <td className="px-3 py-2">{line.productId}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(line.quantity)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(line.orderedQty)}</td>
                  <td className="px-3 py-2 text-right font-medium">{formatNumber(line.remainingQty)}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(line.unitPrice)}</td>
                  <td className="px-3 py-2">
                    <input
                      placeholder={line.remainingQty}
                      value={quantities[line.id] ?? ""}
                      onChange={(e) => setQuantities((prev) => ({ ...prev, [line.id]: e.target.value }))}
                      className="w-full"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">受注確定</h2>
        <p className="mt-1 text-xs text-slate-600">
          伝票単位で全明細を一括確定するか、上表でチェックした明細のみを指定数量で確定できます（数量未入力の場合は残数がそのまま使われます）。
        </p>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="mt-3 flex gap-2">
          <button
            onClick={handleConfirmWhole}
            disabled={busy}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            伝票単位で受注確定
          </button>
          <button
            onClick={handleConfirmSelected}
            disabled={busy}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          >
            選択した明細で受注確定
          </button>
        </div>
      </section>
    </div>
  );
}
