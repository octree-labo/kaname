"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { WarehouseOut } from "@/lib/types";

/**
 * 仕入・売上の明細で、入庫・出庫する倉庫を選ぶ。
 * 空のまま登録すると、サーバー側で既定の倉庫（いちばん古い倉庫）が使われる。
 */
export function WarehouseSelect({
  id,
  value,
  onChange,
  emptyLabel = "既定の倉庫",
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  emptyLabel?: string;
}) {
  const { data: warehouses } = useSWR<WarehouseOut[]>("/api/warehouses", fetcher);
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="mt-1 w-full">
      <option value="">{emptyLabel}</option>
      {(warehouses ?? []).map((w) => (
        <option key={w.id} value={w.id}>
          {w.warehouseCode} {w.name}
        </option>
      ))}
    </select>
  );
}
