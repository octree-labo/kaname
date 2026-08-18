"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, ApiError, fetcher } from "@/lib/api";
import type { ProductOut } from "@/lib/types";
import { DataTable, type Column } from "@/components/DataTable";
import { useGuestGuard } from "@/lib/useGuestGuard";
import { GuestBlockedModal } from "@/components/GuestBlockedModal";

export default function ProductsPage() {
  const { blocked, setBlocked, guard } = useGuestGuard();
  const [keyword, setKeyword] = useState("");
  const { data, mutate } = useSWR<ProductOut[]>(
    `/api/products${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`,
    fetcher
  );

  const [showForm, setShowForm] = useState(false);
  const [productCode, setProductCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("個");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (guard()) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.post<ProductOut>("/api/products", {
        productCode: productCode || undefined,
        name,
        category: category || undefined,
        unit,
      });
      setProductCode("");
      setName("");
      setCategory("");
      setShowForm(false);
      mutate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登録に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  const columns: Column<ProductOut>[] = [
    { key: "productCode", label: "商品コード", sortable: true },
    { key: "name", label: "商品名", sortable: true },
    { key: "category", label: "分類", sortable: true, render: (r) => r.category ?? "-" },
    { key: "unit", label: "単位", sortable: true },
    { key: "isActive", label: "状態", sortable: true, render: (r) => (r.isActive ? "有効" : "無効") },
    {
      key: "edit",
      label: "",
      render: (r) => (
        <a href={`/products/${r.id}/edit`} className="text-slate-700 hover:underline">
          編集
        </a>
      ),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <GuestBlockedModal open={blocked} onClose={() => setBlocked(false)} />
      <div className="flex shrink-0 items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">商品</h1>
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
            <label htmlFor="productCode" className="block text-sm font-medium text-slate-700">商品コード</label>
            <input
              id="productCode"
              value={productCode}
              onChange={(e) => setProductCode(e.target.value)}
              placeholder="空欄で自動採番（000001〜）"
              className="mt-1 w-full"
            />
          </div>
          <div>
            <label htmlFor="unit" className="block text-sm font-medium text-slate-700">単位</label>
            <input id="unit" required value={unit} onChange={(e) => setUnit(e.target.value)} className="mt-1 w-full" />
          </div>
          <div className="col-span-2">
            <label htmlFor="productName" className="block text-sm font-medium text-slate-700">商品名</label>
            <input id="productName" required value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full" />
          </div>
          <div className="col-span-2">
            <label htmlFor="category" className="block text-sm font-medium text-slate-700">分類</label>
            <input id="category" value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 w-full" />
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

      <input
        aria-label="商品名・コードで検索"
        placeholder="商品名・コードで検索"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        className="mt-4 w-72 shrink-0"
      />

      <div className="mt-4 min-h-0 flex-1">
        <DataTable columns={columns} rows={data ?? []} />
      </div>
    </div>
  );
}
