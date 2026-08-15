/**
 * 数量・単価から金額を自動計算する明細行の共通ロジック。
 * 数量・単価が両方入力されていれば金額はサーバー側で自動計算されるため送信しない。
 * どちらか一方でも未入力の場合のみ、金額を手入力として送信する。
 */
export interface ProductLineValue {
  productId: string;
  quantity: string;
  unitPrice: string;
  amount: string;
}

export function isManualAmount(line: { quantity: string; unitPrice: string }): boolean {
  return line.quantity.trim() === "" || line.unitPrice.trim() === "";
}

export function buildProductLinePayload(line: ProductLineValue): Record<string, unknown> {
  const hasQty = line.quantity.trim() !== "";
  const hasPrice = line.unitPrice.trim() !== "";
  const payload: Record<string, unknown> = { productId: Number(line.productId) };
  if (hasQty) payload.quantity = Number(line.quantity);
  if (hasPrice) payload.unitPrice = Number(line.unitPrice);
  if (!hasQty || !hasPrice) payload.amount = Number(line.amount);
  return payload;
}
