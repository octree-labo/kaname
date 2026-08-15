"use client";

import { api } from "@/lib/api";
import type { ProductOut } from "@/lib/types";
import { SearchSelect } from "@/components/SearchSelect";

function productLabel(p: ProductOut): string {
  return `${p.productCode} ${p.name}`.trim();
}

export function ProductPicker({
  id,
  value,
  onChange,
  placeholder = "コード・商品名で検索",
  required,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <SearchSelect
      id={id}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      fetchOptions={async (keyword) => {
        const list = await api.get<ProductOut[]>(`/api/products?keyword=${encodeURIComponent(keyword)}&page_size=20`);
        return list.map((p) => ({ id: p.id, label: productLabel(p) }));
      }}
      fetchLabel={async (productId) => {
        try {
          const p = await api.get<ProductOut>(`/api/products/${productId}`);
          return productLabel(p);
        } catch {
          return null;
        }
      }}
    />
  );
}
