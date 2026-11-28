"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { DocumentModuleConfig } from "@/lib/documentModules";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductLineFields } from "@/components/ProductLineFields";
import { buildProductLinePayload, type ProductLineValue } from "@/lib/lineHelpers";
import { useGuestGuard } from "@/lib/useGuestGuard";
import { GuestBlockedModal } from "@/components/GuestBlockedModal";
import { UpstreamImport } from "@/components/document/UpstreamImport";
import { WarehouseSelect } from "@/components/WarehouseSelect";
import type { OpenLineOut } from "@/lib/types";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

interface ProductLineRow extends ProductLineValue {
  upstreamLineId: string;
  warehouseId?: string;
  /** 取り込んだ上位明細の表示（例: SO000012-1） */
  upstreamText?: string;
}

interface AmountLineRow {
  amount: string;
  upstreamLineId: string;
  upstreamText?: string;
}

function isBlankProductRow(l: ProductLineRow): boolean {
  return !l.productId && !l.quantity && !l.unitPrice && !l.amount && !l.upstreamLineId;
}

export function DocumentNewPage({ config }: { config: DocumentModuleConfig }) {
  const router = useRouter();
  const { blocked, setBlocked, guard } = useGuestGuard();
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

  function importUpstream(lines: OpenLineOut[]) {
    // 取引先がまだ空なら、取り込んだ伝票の取引先を入れる（受注→発注は取引先が別なので入れない）
    if (!partnerId && config.openLinesKind !== "order_for_purchase" && lines.length > 0) {
      setPartnerId(String(lines[0].partnerId));
    }
    if (config.lineKind === "product") {
      const rows: ProductLineRow[] = lines.map((l) => {
        const hasPrice = l.unitPrice !== null && l.remainingQty !== null;
        return {
          productId: String(l.productId),
          quantity: l.remainingQty !== null ? String(Number(l.remainingQty)) : "",
          unitPrice: hasPrice ? String(Number(l.unitPrice)) : "",
          amount: hasPrice ? "" : String(Number(l.amount)),
          upstreamLineId: String(l.lineId),
          upstreamText: `${l.documentNo}-${l.lineNo}`,
        };
      });
      setProductLines((prev) => [...prev.filter((l) => !isBlankProductRow(l)), ...rows]);
    } else {
      const rows: AmountLineRow[] = lines.map((l) => ({
        amount: String(Number(l.remainingAmount ?? l.amount)),
        upstreamLineId: String(l.lineId),
        upstreamText: `${l.documentNo}-${l.lineNo}`,
      }));
      setAmountLines((prev) => [...prev.filter((l) => l.amount || l.upstreamLineId), ...rows]);
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
    if (guard()) return;
    setError(null);
    setSubmitting(true);
    try {
      const lines =
        config.lineKind === "product"
          ? productLines.map((l) => ({
              ...buildProductLinePayload(l),
              ...(config.hasWarehouse && l.warehouseId ? { warehouseId: Number(l.warehouseId) } : {}),
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

  return (
    <div className="max-w-2xl">
      <GuestBlockedModal open={blocked} onClose={() => setBlocked(false)} />
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
          <div className="flex items-center justify-between gap-2">
            <label className="block text-sm font-medium text-slate-700">明細</label>
            <div className="flex items-center gap-2">
              <UpstreamImport config={config} partnerId={partnerId} onImport={importUpstream} />
              <button
              type="button"
              onClick={addLine}
              className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
            >
              + 行を追加
              </button>
            </div>
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
                          prev.map((l, idx) =>
                            idx === i
                              ? { ...next, upstreamLineId: l.upstreamLineId, upstreamText: l.upstreamText, warehouseId: l.warehouseId }
                              : l
                          )
                        )
                      }
                    />
                    {config.hasWarehouse && (
                      <div className="w-36">
                        <label className="block text-xs text-slate-600">{config.warehouseLabel}</label>
                        <WarehouseSelect
                          value={line.warehouseId ?? ""}
                          onChange={(v) =>
                            setProductLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, warehouseId: v } : l)))
                          }
                        />
                      </div>
                    )}
                    {config.upstreamLineField && (
                      <div className="w-40">
                        <label className="block text-xs text-slate-600">{config.upstreamLabel}</label>
                        <input
                          value={line.upstreamLineId}
                          onChange={(e) =>
                            setProductLines((prev) =>
                              prev.map((l, idx) => (idx === i ? { ...l, upstreamLineId: e.target.value, upstreamText: undefined } : l))
                            )
                          }
                          className="mt-1 w-full"
                        />
                        {line.upstreamText && (
                          <p className="mt-0.5 text-[11px] text-sky-700">連携: {line.upstreamText}</p>
                        )}
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
                              prev.map((l, idx) => (idx === i ? { ...l, upstreamLineId: e.target.value, upstreamText: undefined } : l))
                            )
                          }
                          className="mt-1 w-full"
                        />
                        {line.upstreamText && (
                          <p className="mt-0.5 text-[11px] text-sky-700">連携: {line.upstreamText}</p>
                        )}
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
