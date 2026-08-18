"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { PriceMasterOut, PriceType } from "@/lib/types";
import { DataTable, type Column } from "@/components/DataTable";
import { formatNumber } from "@/lib/format";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductPicker } from "@/components/ProductPicker";
import { useGuestGuard } from "@/lib/useGuestGuard";
import { GuestBlockedModal } from "@/components/GuestBlockedModal";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function PriceMasterPage() {
  const { blocked, setBlocked, guard } = useGuestGuard();
  const [partnerFilter, setPartnerFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");

  const params = new URLSearchParams();
  if (partnerFilter) params.set("partner_id", partnerFilter);
  if (productFilter) params.set("product_id", productFilter);
  const query = params.toString();

  const { data, mutate } = useSWR<PriceMasterOut[]>(`/api/price-master${query ? `?${query}` : ""}`, fetcher);

  const [showForm, setShowForm] = useState(false);
  const [priceType, setPriceType] = useState<PriceType>("sales");
  const [partnerId, setPartnerId] = useState("");
  const [productId, setProductId] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [effectiveStartDate, setEffectiveStartDate] = useState(today());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (guard()) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.post("/api/price-master", {
        priceType,
        partnerId: partnerId ? Number(partnerId) : undefined,
        productId: Number(productId),
        unitPrice: Number(unitPrice),
        effectiveStartDate,
      });
      setShowForm(false);
      setPartnerId("");
      setProductId("");
      setUnitPrice("");
      mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  const columns: Column<PriceMasterOut>[] = [
    { key: "priceType", label: "種別", sortable: true, render: (r) => (r.priceType === "sales" ? "販売単価" : "仕入単価") },
    {
      key: "productName",
      label: "商品",
      sortable: true,
      render: (r) => (r.productCode ? `${r.productCode} ${r.productName ?? ""}` : r.productId),
    },
    {
      key: "partnerName",
      label: "取引先",
      sortable: true,
      render: (r) => (r.partnerCode ? `${r.partnerCode} ${r.partnerName ?? ""}` : "(標準)"),
    },
    { key: "unitPrice", label: "単価", align: "right", sortable: true, sortValue: (r) => Number(r.unitPrice), render: (r) => formatNumber(r.unitPrice) },
    { key: "effectiveStartDate", label: "適用開始日", sortable: true },
    { key: "effectiveEndDate", label: "適用終了日", sortable: true, render: (r) => r.effectiveEndDate ?? "-" },
    {
      key: "edit",
      label: "",
      render: (r) => (
        <a href={`/price-master/${r.id}/edit`} className="text-slate-700 hover:underline">
          編集
        </a>
      ),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <GuestBlockedModal open={blocked} onClose={() => setBlocked(false)} />
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">単価マスタ</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          {showForm ? "閉じる" : "新規登録"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mt-4 grid shrink-0 max-w-2xl grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-4"
        >
          <div>
            <label htmlFor="priceType" className="block text-sm font-medium text-slate-700">種別</label>
            <select id="priceType" value={priceType} onChange={(e) => setPriceType(e.target.value as PriceType)} className="mt-1 w-full">
              <option value="sales">販売単価</option>
              <option value="purchase">仕入単価</option>
            </select>
          </div>
          <div>
            <label htmlFor="pmPartnerId" className="block text-sm font-medium text-slate-700">取引先（空欄=標準単価）</label>
            <div className="mt-1">
              <PartnerPicker id="pmPartnerId" value={partnerId} onChange={setPartnerId} />
            </div>
          </div>
          <div>
            <label htmlFor="pmProductId" className="block text-sm font-medium text-slate-700">商品</label>
            <div className="mt-1">
              <ProductPicker id="pmProductId" value={productId} onChange={setProductId} required />
            </div>
          </div>
          <div>
            <label htmlFor="pmUnitPrice" className="block text-sm font-medium text-slate-700">単価</label>
            <input id="pmUnitPrice" required type="number" step="0.01" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} className="mt-1 w-full" />
          </div>
          <div>
            <label htmlFor="pmEffectiveStartDate" className="block text-sm font-medium text-slate-700">適用開始日</label>
            <input
              id="pmEffectiveStartDate"
              type="date"
              required
              value={effectiveStartDate}
              onChange={(e) => setEffectiveStartDate(e.target.value)}
              className="mt-1 w-full"
            />
          </div>
          {error && <p className="col-span-2 text-sm text-red-600">{error}</p>}
          <div className="col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              登録
            </button>
          </div>
        </form>
      )}

      <div className="mt-4 grid shrink-0 grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4">
        <div>
          <label className="block text-xs text-slate-600">取引先で絞込み</label>
          <PartnerPicker value={partnerFilter} onChange={setPartnerFilter} />
        </div>
        <div>
          <label className="block text-xs text-slate-600">商品で絞込み</label>
          <ProductPicker value={productFilter} onChange={setProductFilter} />
        </div>
      </div>

      <div className="mt-4 min-h-0 flex-1">
        <DataTable columns={columns} rows={data ?? []} />
      </div>
    </div>
  );
}
