"use client";

import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { InventoryStockOut, InventoryAllocationOut, InventoryAvailabilityOut, WarehouseOut } from "@/lib/types";
import { formatNumber } from "@/lib/format";
import { DataTable, type Column } from "@/components/DataTable";
import { ProductPicker } from "@/components/ProductPicker";

const STAGE_LABEL: Record<string, string> = {
  quotation: "見積時点",
  order: "受注時点",
  sales: "売上時点",
};

interface StockRow extends InventoryStockOut {
  id: number; // DataTable要件のため合成
}

type AllocationRow = InventoryAllocationOut;

interface AvailabilityRow extends InventoryAvailabilityOut {
  id: number; // DataTable要件のため合成
}

export default function InventoryPage() {
  const [stockProductId, setStockProductId] = useState("");
  const [stockWarehouseId, setStockWarehouseId] = useState("");
  const [allocProductId, setAllocProductId] = useState("");
  const [allocStage, setAllocStage] = useState("");

  const [availKeyword, setAvailKeyword] = useState("");
  const availParams = new URLSearchParams();
  if (availKeyword) availParams.set("keyword", availKeyword);
  const { data: availability } = useSWR<InventoryAvailabilityOut[]>(
    `/api/inventory/availability?${availParams.toString()}`,
    fetcher
  );
  const availRows: AvailabilityRow[] = (availability ?? []).map((a) => ({ ...a, id: a.productId }));
  const qtyCol = (key: keyof InventoryAvailabilityOut, label: string): Column<AvailabilityRow> => ({
    key,
    label,
    align: "right",
    sortable: true,
    sortValue: (r) => Number(r[key]),
    render: (r) => formatNumber(r[key] as string),
  });
  const availColumns: Column<AvailabilityRow>[] = [
    {
      key: "productName",
      label: "商品",
      sortable: true,
      render: (r) => `${r.productCode} ${r.productName}`,
    },
    qtyCol("onHand", "在庫数"),
    qtyCol("allocated", "引当中"),
    qtyCol("incoming", "入荷予定"),
    {
      key: "available",
      label: "使える見込み",
      align: "right",
      sortable: true,
      sortValue: (r) => Number(r.available),
      render: (r) => (
        <span className={Number(r.available) < 0 ? "font-semibold text-red-600" : "font-semibold"}>
          {formatNumber(r.available)} {r.unit}
        </span>
      ),
    },
  ];

  const { data: warehouses } = useSWR<WarehouseOut[]>("/api/warehouses", fetcher);

  const stockParams = new URLSearchParams();
  if (stockProductId) stockParams.set("product_id", stockProductId);
  if (stockWarehouseId) stockParams.set("warehouse_id", stockWarehouseId);
  const { data: stocks } = useSWR<InventoryStockOut[]>(`/api/inventory/stocks?${stockParams.toString()}`, fetcher);

  const allocParams = new URLSearchParams();
  if (allocProductId) allocParams.set("product_id", allocProductId);
  if (allocStage) allocParams.set("stage", allocStage);
  const { data: allocations } = useSWR<InventoryAllocationOut[]>(`/api/inventory/allocations?${allocParams.toString()}`, fetcher);

  const stockRows: StockRow[] = (stocks ?? []).map((s, i) => ({ ...s, id: i }));
  const allocRows: AllocationRow[] = (allocations ?? []).map((a) => ({ ...a }));

  const stockColumns: Column<StockRow>[] = [
    {
      key: "productName",
      label: "商品",
      sortable: true,
      render: (r) => (r.productCode ? `${r.productCode} ${r.productName ?? ""}` : r.productId),
    },
    {
      key: "warehouseName",
      label: "倉庫",
      sortable: true,
      render: (r) => (r.warehouseCode ? `${r.warehouseCode} ${r.warehouseName ?? ""}` : r.warehouseId),
    },
    {
      key: "quantityOnHand",
      label: "在庫数",
      align: "right",
      sortable: true,
      sortValue: (r) => Number(r.quantityOnHand),
      render: (r) => formatNumber(r.quantityOnHand),
    },
  ];

  const allocColumns: Column<AllocationRow>[] = [
    {
      key: "allocationStage",
      label: "引当段階",
      sortable: true,
      render: (r) => STAGE_LABEL[r.allocationStage] ?? r.allocationStage,
    },
    {
      key: "productName",
      label: "商品",
      sortable: true,
      render: (r) => (r.productCode ? `${r.productCode} ${r.productName ?? ""}` : r.productId),
    },
    {
      key: "warehouseName",
      label: "倉庫",
      sortable: true,
      render: (r) => (r.warehouseCode ? `${r.warehouseCode} ${r.warehouseName ?? ""}` : r.warehouseId ?? "-"),
    },
    {
      key: "quantity",
      label: "数量",
      align: "right",
      sortable: true,
      sortValue: (r) => Number(r.quantity),
      render: (r) => formatNumber(r.quantity),
    },
    {
      key: "line",
      label: "参照明細",
      render: (r) => r.quotationLineId ?? r.orderLineId ?? r.salesLineId ?? "-",
    },
  ];

  return (
    <div className="flex h-full flex-col gap-8 overflow-hidden">
      <h1 className="shrink-0 text-xl font-semibold text-slate-900">在庫・引当</h1>

      <section className="flex min-h-0 flex-1 flex-col">
        <h2 className="shrink-0 text-sm font-semibold text-slate-700">使える在庫の見込み</h2>
        <p className="mt-1 shrink-0 text-xs text-slate-600">
          在庫数 − 引当中 + 入荷予定（発注残）。見積・受注の引当は、次の伝票に進んでいない残りの分だけを数えるので、同じ在庫を二重に押さえません。
        </p>
        <div className="mt-2 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-4">
          <div>
            <label htmlFor="availKeyword" className="block text-xs text-slate-600">商品コード・商品名</label>
            <input id="availKeyword" value={availKeyword} onChange={(e) => setAvailKeyword(e.target.value)} className="w-full" />
          </div>
        </div>
        <div className="mt-2 min-h-0 flex-1">
          <DataTable columns={availColumns} rows={availRows} />
        </div>
      </section>

      <section className="flex min-h-0 flex-1 flex-col">
        <h2 className="shrink-0 text-sm font-semibold text-slate-700">在庫現在数</h2>
        <div className="mt-2 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-4">
          <div>
            <label className="block text-xs text-slate-600">商品で絞込み</label>
            <ProductPicker value={stockProductId} onChange={setStockProductId} />
          </div>
          <div>
            <label className="block text-xs text-slate-600">倉庫で絞込み</label>
            <select value={stockWarehouseId} onChange={(e) => setStockWarehouseId(e.target.value)} className="w-full">
              <option value="">すべて</option>
              {(warehouses ?? []).map((w) => (
                <option key={w.id} value={w.id}>
                  {w.warehouseCode} {w.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-2 min-h-0 flex-1">
          <DataTable columns={stockColumns} rows={stockRows} />
        </div>
      </section>

      <section className="flex min-h-0 flex-1 flex-col">
        <h2 className="shrink-0 text-sm font-semibold text-slate-700">在庫引当（見積/受注/売上時点で独立管理）</h2>
        <div className="mt-2 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-4">
          <div>
            <label className="block text-xs text-slate-600">商品で絞込み</label>
            <ProductPicker value={allocProductId} onChange={setAllocProductId} />
          </div>
          <div>
            <label className="block text-xs text-slate-600">引当段階</label>
            <select value={allocStage} onChange={(e) => setAllocStage(e.target.value)} className="w-full">
              <option value="">すべて</option>
              <option value="quotation">見積時点</option>
              <option value="order">受注時点</option>
              <option value="sales">売上時点</option>
            </select>
          </div>
        </div>
        <div className="mt-2 min-h-0 flex-1">
          <DataTable columns={allocColumns} rows={allocRows} />
        </div>
      </section>
    </div>
  );
}
