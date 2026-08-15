"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { QuotationDetailOut } from "@/lib/types";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductPicker } from "@/components/ProductPicker";

interface LineEdit {
  id: number;
  productId: string;
  quantity: string;
  unitPrice: string;
}

export default function EditQuotationPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data } = useSWR<QuotationDetailOut>(`/api/quotations/${params.id}`, fetcher);

  const [partnerId, setPartnerId] = useState("");
  const [quotationDate, setQuotationDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [conditionText, setConditionText] = useState("");
  const [lines, setLines] = useState<LineEdit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!data) return;
    // SWRで取得した既存データを編集用の下書きstateへ一度だけ複製する
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPartnerId(String(data.partnerId));
    setQuotationDate(data.quotationDate);
    setExpiryDate(data.expiryDate ?? "");
    setConditionText(data.conditionText ?? "");
    setLines(
      data.lines.map((l) => ({ id: l.id, productId: String(l.productId), quantity: l.quantity, unitPrice: l.unitPrice }))
    );
  }, [data]);

  if (!data) return <p className="text-sm text-slate-600">読み込み中...</p>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.patch(`/api/quotations/${params.id}`, {
        partnerId: Number(partnerId),
        quotationDate,
        expiryDate: expiryDate || null,
        conditionText: conditionText || null,
        lines: lines.map((l) => ({
          id: l.id,
          productId: Number(l.productId),
          quantity: Number(l.quantity),
          unitPrice: Number(l.unitPrice),
        })),
      });
      router.push(`/quotations/${params.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">見積 編集</h1>
      <p className="mt-1 text-xs text-slate-600">
        既存明細の商品・数量・単価のみ変更できます。明細の追加・削除には対応していません。
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="editPartnerId" className="block text-sm font-medium text-slate-700">取引先</label>
            <div className="mt-1">
              <PartnerPicker id="editPartnerId" value={partnerId} onChange={setPartnerId} required />
            </div>
          </div>
          <div>
            <label htmlFor="editQuotationDate" className="block text-sm font-medium text-slate-700">見積日</label>
            <input
              id="editQuotationDate"
              type="date"
              required
              value={quotationDate}
              onChange={(e) => setQuotationDate(e.target.value)}
              className="mt-1 w-full"
            />
          </div>
          <div>
            <label htmlFor="editExpiryDate" className="block text-sm font-medium text-slate-700">見積期限</label>
            <input
              id="editExpiryDate"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className="mt-1 w-full"
            />
          </div>
        </div>

        <div>
          <label htmlFor="editConditionText" className="block text-sm font-medium text-slate-700">見積条件</label>
          <textarea
            id="editConditionText"
            value={conditionText}
            onChange={(e) => setConditionText(e.target.value)}
            className="mt-1 w-full"
            rows={2}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">明細</label>
          <div className="mt-2 space-y-2">
            {lines.map((line, i) => (
              <div key={line.id} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                <div className="flex-1">
                  <label className="block text-xs text-slate-600">商品</label>
                  <div className="mt-1">
                    <ProductPicker
                      value={line.productId}
                      onChange={(v) => setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, productId: v } : l)))}
                      required
                    />
                  </div>
                </div>
                <div className="w-24">
                  <label className="block text-xs text-slate-600">数量</label>
                  <input
                    required
                    type="number"
                    step="0.001"
                    value={line.quantity}
                    onChange={(e) => setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, quantity: e.target.value } : l)))}
                    className="mt-1 w-full"
                  />
                </div>
                <div className="w-28">
                  <label className="block text-xs text-slate-600">単価</label>
                  <input
                    required
                    type="number"
                    step="0.01"
                    value={line.unitPrice}
                    onChange={(e) => setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, unitPrice: e.target.value } : l)))}
                    className="mt-1 w-full"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            保存
          </button>
          <button
            type="button"
            onClick={() => router.push(`/quotations/${params.id}`)}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
