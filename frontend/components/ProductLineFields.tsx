"use client";

import { ProductPicker } from "@/components/ProductPicker";
import { isManualAmount, type ProductLineValue } from "@/lib/lineHelpers";

/** 商品/数量/単価/金額の入力欄セット。数量・単価が両方揃っていれば金額は自動計算扱いとして無効化する。 */
export function ProductLineFields({
  value,
  onChange,
}: {
  value: ProductLineValue;
  onChange: (next: ProductLineValue) => void;
}) {
  const manual = isManualAmount(value);

  return (
    <>
      <div className="flex-1">
        <label className="block text-xs text-slate-600">商品</label>
        <div className="mt-1">
          <ProductPicker value={value.productId} onChange={(v) => onChange({ ...value, productId: v })} required />
        </div>
      </div>
      <div className="w-24">
        <label className="block text-xs text-slate-600">数量</label>
        <input
          type="number"
          step="0.001"
          value={value.quantity}
          onChange={(e) => onChange({ ...value, quantity: e.target.value })}
          className="mt-1 w-full"
        />
      </div>
      <div className="w-28">
        <label className="block text-xs text-slate-600">単価</label>
        <input
          type="number"
          step="0.01"
          value={value.unitPrice}
          onChange={(e) => onChange({ ...value, unitPrice: e.target.value })}
          className="mt-1 w-full"
        />
      </div>
      <div className="w-28">
        <label className="block text-xs text-slate-600">{manual ? "金額（手入力）" : "金額"}</label>
        <input
          type="number"
          step="1"
          required={manual}
          disabled={!manual}
          value={manual ? value.amount : ""}
          placeholder={manual ? "" : "自動計算"}
          onChange={(e) => onChange({ ...value, amount: e.target.value })}
          className="mt-1 w-full disabled:bg-slate-100 disabled:text-slate-400"
        />
      </div>
    </>
  );
}
