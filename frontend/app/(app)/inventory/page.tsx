"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { InventoryStockOut, InventoryAllocationOut } from "@/lib/types";
import { formatNumber } from "@/lib/format";

const STAGE_LABEL: Record<string, string> = {
  quotation: "見積時点",
  order: "受注時点",
  sales: "売上時点",
};

export default function InventoryPage() {
  const { data: stocks } = useSWR<InventoryStockOut[]>("/api/inventory/stocks", fetcher);
  const { data: allocations } = useSWR<InventoryAllocationOut[]>("/api/inventory/allocations", fetcher);

  return (
    <div className="max-w-3xl space-y-8">
      <h1 className="text-xl font-semibold text-slate-900">在庫・引当</h1>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">在庫現在数</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">商品ID</th>
                <th className="px-3 py-2">倉庫ID</th>
                <th className="px-3 py-2 text-right">在庫数</th>
              </tr>
            </thead>
            <tbody>
              {(stocks ?? []).map((s) => (
                <tr key={`${s.productId}-${s.warehouseId}`} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{s.productId}</td>
                  <td className="px-3 py-2">{s.warehouseId}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(s.quantityOnHand)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-slate-700">在庫引当（見積/受注/売上時点で独立管理）</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-600">
                <th className="px-3 py-2">引当段階</th>
                <th className="px-3 py-2">商品ID</th>
                <th className="px-3 py-2">倉庫ID</th>
                <th className="px-3 py-2 text-right">数量</th>
                <th className="px-3 py-2">参照明細</th>
              </tr>
            </thead>
            <tbody>
              {(allocations ?? []).map((a) => (
                <tr key={a.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{STAGE_LABEL[a.allocationStage] ?? a.allocationStage}</td>
                  <td className="px-3 py-2">{a.productId}</td>
                  <td className="px-3 py-2">{a.warehouseId ?? "-"}</td>
                  <td className="px-3 py-2 text-right">{formatNumber(a.quantity)}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {a.quotationLineId ?? a.orderLineId ?? a.salesLineId ?? "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
