"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { QuotationOut } from "@/lib/types";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductLineFields } from "@/components/ProductLineFields";
import { buildProductLinePayload, type ProductLineValue } from "@/lib/lineHelpers";
import { useCurrentUser } from "@/lib/useCurrentUser";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewQuotationPage() {
  const router = useRouter();
  const { isGuest } = useCurrentUser();
  const [partnerId, setPartnerId] = useState("");
  const [quotationDate, setQuotationDate] = useState(today());
  const [expiryDate, setExpiryDate] = useState("");
  const [conditionText, setConditionText] = useState("");
  const [lines, setLines] = useState<ProductLineValue[]>([
    { productId: "", quantity: "", unitPrice: "", amount: "" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function addLine() {
    setLines((prev) => [...prev, { productId: "", quantity: "", unitPrice: "", amount: "" }]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.post<QuotationOut>("/api/quotations", {
        partnerId: Number(partnerId),
        quotationDate,
        expiryDate: expiryDate || undefined,
        conditionText: conditionText || undefined,
        lines: lines.map((l) => buildProductLinePayload(l)),
      });
      router.push(`/quotations/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  if (isGuest) {
    return (
      <div className="max-w-2xl">
        <h1 className="text-xl font-semibold text-slate-900">見積 新規作成</h1>
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          ゲストは閲覧のみで、新規作成はできません。
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">見積 新規作成</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="qPartnerId" className="block text-sm font-medium text-slate-700">取引先</label>
            <div className="mt-1">
              <PartnerPicker id="qPartnerId" value={partnerId} onChange={setPartnerId} required />
            </div>
          </div>
          <div>
            <label htmlFor="quotationDate" className="block text-sm font-medium text-slate-700">見積日</label>
            <input
              id="quotationDate"
              type="date"
              required
              value={quotationDate}
              onChange={(e) => setQuotationDate(e.target.value)}
              className="mt-1 w-full"
            />
          </div>
          <div>
            <label htmlFor="expiryDate" className="block text-sm font-medium text-slate-700">見積期限</label>
            <input id="expiryDate" type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} className="mt-1 w-full" />
          </div>
        </div>

        <div>
          <label htmlFor="conditionText" className="block text-sm font-medium text-slate-700">見積条件</label>
          <textarea
            id="conditionText"
            value={conditionText}
            onChange={(e) => setConditionText(e.target.value)}
            className="mt-1 w-full"
            rows={2}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-slate-700">明細</label>
            <button
              type="button"
              onClick={addLine}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
            >
              + 行を追加
            </button>
          </div>
          <p className="mt-1 text-xs text-slate-600">
            数量・単価を両方入力すると金額は自動計算されます（取引先の丸め区分を適用）。どちらか一方でも空欄の場合は金額を直接入力してください。
          </p>
          <div className="mt-2 space-y-2">
            {lines.map((line, i) => (
              <div key={i} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                <ProductLineFields
                  value={line}
                  onChange={(next) => setLines((prev) => prev.map((l, idx) => (idx === i ? next : l)))}
                />
                <button
                  type="button"
                  onClick={() => removeLine(i)}
                  className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
                >
                  削除
                </button>
              </div>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          作成
        </button>
      </form>
    </div>
  );
}
