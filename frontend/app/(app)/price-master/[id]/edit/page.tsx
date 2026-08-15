"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { PriceMasterOut, PriceType } from "@/lib/types";
import { PartnerPicker } from "@/components/PartnerPicker";
import { ProductPicker } from "@/components/ProductPicker";

export default function EditPriceMasterPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data } = useSWR<PriceMasterOut>(`/api/price-master/${params.id}`, fetcher);

  const [priceType, setPriceType] = useState<PriceType>("sales");
  const [partnerId, setPartnerId] = useState("");
  const [productId, setProductId] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [effectiveStartDate, setEffectiveStartDate] = useState("");
  const [effectiveEndDate, setEffectiveEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!data) return;
    // SWRで取得した既存データを編集用の下書きstateへ一度だけ複製する
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPriceType(data.priceType);
    setPartnerId(data.partnerId ? String(data.partnerId) : "");
    setProductId(String(data.productId));
    setUnitPrice(data.unitPrice);
    setEffectiveStartDate(data.effectiveStartDate);
    setEffectiveEndDate(data.effectiveEndDate ?? "");
  }, [data]);

  if (!data) return <p className="text-sm text-slate-600">読み込み中...</p>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.patch(`/api/price-master/${params.id}`, {
        priceType,
        partnerId: partnerId ? Number(partnerId) : null,
        productId: Number(productId),
        unitPrice: Number(unitPrice),
        effectiveStartDate,
        effectiveEndDate: effectiveEndDate || null,
      });
      router.push("/price-master");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold text-slate-900">単価マスタ 編集</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="startDate" className="block text-sm font-medium text-slate-700">適用開始日</label>
            <input id="startDate" type="date" required value={effectiveStartDate} onChange={(e) => setEffectiveStartDate(e.target.value)} className="mt-1 w-full" />
          </div>
          <div>
            <label htmlFor="endDate" className="block text-sm font-medium text-slate-700">適用終了日</label>
            <input id="endDate" type="date" value={effectiveEndDate} onChange={(e) => setEffectiveEndDate(e.target.value)} className="mt-1 w-full" />
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
            onClick={() => router.push("/price-master")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
