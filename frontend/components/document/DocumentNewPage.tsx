"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductLineFields } from "@/components/ProductLineFields";
import { buildProductLinePayload, type ProductLineValue } from "@/lib/lineHelpers";
import { useCurrentUser } from "@/lib/useCurrentUser";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

interface ProductLineRow extends ProductLineValue {
  upstreamLineId: string;
}

interface AmountLineRow {
  amount: string;
  upstreamLineId: string;
}

export function DocumentNewPage({ config }: { config: DocumentModuleConfig }) {
  const router = useRouter();
  const { isGuest } = useCurrentUser();
  const [partnerId, setPartnerId] = useState("");
  const [date, setDate] = useState(today());
  const [productLines, setProductLines] = useState<ProductLineRow[]>([
    { productId: "", quantity: "", unitPrice: "", amount: "", upstreamLineId: "" },
  ]);
  const [amountLines, setAmountLines] = useState<AmountLineRow[]>([
    { amount: "", upstreamLineId: "" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function addLine() {
    if (config.lineKind === "product") {
      setProductLines((prev) => [...prev, { productId: "", quantity: "", unitPrice: "", amount: "", upstreamLineId: "" }]);
    } else {
      setAmountLines((prev) => [...prev, { amount: "", upstreamLineId: "" }]);
    }
  }

  function removeLine(index: number) {
    if (config.lineKind === "product") {
      setProductLines((prev) => prev.filter((_, i) => i !== index));
    } else {
      setAmountLines((prev) => prev.filter((_, i) => i !== index));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const lines =
        config.lineKind === "product"
          ? productLines.map((l) => ({
              ...buildProductLinePayload(l),
              ...(config.upstreamLineField && l.upstreamLineId
                ? { [config.upstreamLineField]: Number(l.upstreamLineId) }
                : {}),
            }))
          : amountLines.map((l) => ({
              amount: Number(l.amount),
              ...(config.upstreamLineField && l.upstreamLineId
                ? { [config.upstreamLineField]: Number(l.upstreamLineId) }
                : {}),
            }));

      const created = await api.post<{ id: number }>(config.apiPath, {
        partnerId: Number(partnerId),
        [config.dateField]: date,
        lines,
      });
      router.push(`/${config.key}/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  if (isGuest) {
    return (
      <div className="max-w-2xl">
        <h1 className="text-xl font-semibold text-slate-900">{config.label} 新規作成</h1>
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          ゲストは閲覧のみで、新規作成はできません。
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">{config.label} 新規作成</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="docPartnerId" className="block text-sm font-medium text-slate-700">取引先</label>
            <div className="mt-1">
              <PartnerPicker id="docPartnerId" value={partnerId} onChange={setPartnerId} required />
            </div>
          </div>
          <div>
            <label htmlFor="docDate" className="block text-sm font-medium text-slate-700">{config.dateLabel}</label>
            <input id="docDate" type="date" required value={date} onChange={(e) => setDate(e.target.value)} className="mt-1 w-full" />
          </div>
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
            {config.lineKind === "product"
              ? productLines.map((line, i) => (
                  <div key={i} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                    <ProductLineFields
                      value={line}
                      onChange={(next) =>
                        setProductLines((prev) =>
                          prev.map((l, idx) => (idx === i ? { ...next, upstreamLineId: l.upstreamLineId } : l))
                        )
                      }
                    />
                    {config.upstreamLineField && (
                      <div className="w-40">
                        <label className="block text-xs text-slate-600">{config.upstreamLabel}</label>
                        <input
                          value={line.upstreamLineId}
                          onChange={(e) =>
                            setProductLines((prev) =>
                              prev.map((l, idx) => (idx === i ? { ...l, upstreamLineId: e.target.value } : l))
                            )
                          }
                          className="mt-1 w-full"
                        />
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => removeLine(i)}
                      className="rounded-md border border-slate-300 px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
                    >
                      削除
                    </button>
                  </div>
                ))
              : amountLines.map((line, i) => (
                  <div key={i} className="flex items-end gap-2 rounded-md border border-slate-200 p-3">
                    <div className="w-32">
                      <label className="block text-xs text-slate-600">金額</label>
                      <input
                        required
                        type="number"
                        step="0.01"
                        value={line.amount}
                        onChange={(e) =>
                          setAmountLines((prev) =>
                            prev.map((l, idx) => (idx === i ? { ...l, amount: e.target.value } : l))
                          )
                        }
                        className="mt-1 w-full"
                      />
                    </div>
                    {config.upstreamLineField && (
                      <div className="w-48">
                        <label className="block text-xs text-slate-600">{config.upstreamLabel}</label>
                        <input
                          value={line.upstreamLineId}
                          onChange={(e) =>
                            setAmountLines((prev) =>
                              prev.map((l, idx) => (idx === i ? { ...l, upstreamLineId: e.target.value } : l))
                            )
                          }
                          className="mt-1 w-full"
                        />
                      </div>
                    )}
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
