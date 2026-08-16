"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { ProductOut } from "@/lib/types";
import { PartnerPicker } from "@/components/PartnerPicker";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { isGuest } = useCurrentUser();
  const { data } = useSWR<ProductOut>(`/api/products/${params.id}`, fetcher);

  const [productCode, setProductCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [defaultSupplierId, setDefaultSupplierId] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!data) return;
    // SWRで取得した既存データを編集用の下書きstateへ一度だけ複製する
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProductCode(data.productCode);
    setName(data.name);
    setCategory(data.category ?? "");
    setUnit(data.unit);
    setDefaultSupplierId(data.defaultSupplierId ? String(data.defaultSupplierId) : "");
    setIsActive(data.isActive);
  }, [data]);

  if (!data) return <p className="text-sm text-slate-600">読み込み中...</p>;

  if (isGuest) {
    return (
      <div className="max-w-xl">
        <h1 className="text-xl font-semibold text-slate-900">商品 編集</h1>
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          ゲストは閲覧のみで、編集はできません。
        </p>
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.patch(`/api/products/${params.id}`, {
        productCode,
        name,
        category: category || undefined,
        unit,
        defaultSupplierId: defaultSupplierId ? Number(defaultSupplierId) : undefined,
        isActive,
      });
      router.push("/products");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "更新に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold text-slate-900">商品 編集</h1>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="productCode" className="block text-sm font-medium text-slate-700">商品コード</label>
          <input id="productCode" required value={productCode} onChange={(e) => setProductCode(e.target.value)} className="mt-1 w-full" />
        </div>
        <div>
          <label htmlFor="productName" className="block text-sm font-medium text-slate-700">商品名</label>
          <input id="productName" required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full" />
        </div>
        <div>
          <label htmlFor="category" className="block text-sm font-medium text-slate-700">分類</label>
          <input id="category" value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 w-full" />
        </div>
        <div>
          <label htmlFor="unit" className="block text-sm font-medium text-slate-700">単位</label>
          <input id="unit" required value={unit} onChange={(e) => setUnit(e.target.value)} className="mt-1 w-full" />
        </div>
        <div>
          <label htmlFor="defaultSupplierId" className="block text-sm font-medium text-slate-700">主な仕入先</label>
          <div className="mt-1">
            <PartnerPicker id="defaultSupplierId" value={defaultSupplierId} onChange={setDefaultSupplierId} placeholder="仕入先を検索（任意）" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input id="isActive" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          <label htmlFor="isActive" className="text-sm text-slate-700">有効</label>
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
            onClick={() => router.push("/products")}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            キャンセル
          </button>
        </div>
      </form>
    </div>
  );
}
