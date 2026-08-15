"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { QuotationOut } from "@/lib/types";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

interface LineRow {
  productId: string;
  quantity: string;
  unitPrice: string;
}

export default function NewQuotationPage() {
  const router = useRouter();
  const [partnerId, setPartnerId] = useState("");
  const [quotationDate, setQuotationDate] = useState(today());
  const [expiryDate, setExpiryDate] = useState("");
  const [conditionText, setConditionText] = useState("");
  const [lines, setLines] = useState<LineRow[]>([{ productId: "", quantity: "", unitPrice: "" }]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function addLine() {
    setLines((prev) => [...prev, { productId: "", quantity: "", unitPrice: "" }]);
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
        lines: lines.map((l) => ({
          productId: Number(l.productId),
          quantity: Number(l.quantity),
          unitPrice: Number(l.unitPrice),
        })),
      });
      router.push(`/quotations/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">見積 新規作成</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="qPartnerId" className="block text-sm font-medium text-slate-700">取引先ID</label>
            <input id="qPartnerId" required value={partnerId} onChange={(e) => setPartnerId(e.target.value)} className="mt-1 w-full" />
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
              className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-100"
            >
              + 行を追加
            </button>
          </div>
          <div className="mt-2 space-y-2">
            {lines.map((line, i) => (
              <div key={i} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                <div className="flex-1">
                  <label className="block text-xs text-slate-500">商品ID</label>
                  <input
                    required
                    value={line.productId}
                    onChange={(e) =>
                      setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, productId: e.target.value } : l)))
                    }
                    className="mt-1 w-full"
                  />
                </div>
                <div className="w-24">
                  <label className="block text-xs text-slate-500">数量</label>
                  <input
                    required
                    type="number"
                    step="0.001"
                    value={line.quantity}
                    onChange={(e) =>
                      setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, quantity: e.target.value } : l)))
                    }
                    className="mt-1 w-full"
                  />
                </div>
                <div className="w-28">
                  <label className="block text-xs text-slate-500">単価</label>
                  <input
                    required
                    type="number"
                    step="0.01"
                    value={line.unitPrice}
                    onChange={(e) =>
                      setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, unitPrice: e.target.value } : l)))
                    }
                    className="mt-1 w-full"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeLine(i)}
                  className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-500 hover:bg-slate-100"
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
