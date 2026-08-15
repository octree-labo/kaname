/**
 * バックエンド（FastAPI/Pydantic）が返すレスポンスの型。
 *
 * 注意: 数量・金額などの Decimal 系フィールドは、Pydantic v2 のデフォルト挙動により
 * JSON化されると "10.000" のような文字列で返る。GET系(*Out)は string、
 * フォーム送信で組み立てる POST/PATCH ボディ(*In)は number として扱う。
 */

export type PartnerType = "customer" | "supplier" | "both";
export type ApprovalStatus = "draft" | "pending" | "approved" | "rejected";
export type DocumentStatus = "draft" | "confirmed" | "cancelled";
export type PriceType = "sales" | "purchase";
export type AllocationStage = "quotation" | "order" | "sales";

export interface PartnerDetailOut {
  id: number;
  partnerId: number;
  effectiveDate: string;
  name: string;
  nameKana: string | null;
  representativeName: string | null;
  postalCode: string | null;
  address: string | null;
  phone: string | null;
  fax: string | null;
  email: string | null;
  contactPerson: string | null;
  creditLimit: string | null;
  remarks: string | null;
  createdAt: string;
}

export interface PartnerDetailIn {
  effectiveDate: string;
  name: string;
  nameKana?: string;
  representativeName?: string;
  postalCode?: string;
  address?: string;
  phone?: string;
  fax?: string;
  email?: string;
  contactPerson?: string;
  creditLimit?: number;
  remarks?: string;
}

export interface PartnerOut {
  id: number;
  partnerCode: string;
  partnerType: PartnerType;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface PartnerWithCurrentDetailOut extends PartnerOut {
  currentDetail: PartnerDetailOut | null;
}

export interface ProductOut {
  id: number;
  productCode: string;
  name: string;
  category: string | null;
  unit: string;
  defaultSupplierId: number | null;
  isActive: boolean;
}

export interface PriceMasterOut {
  id: number;
  priceType: PriceType;
  partnerId: number | null;
  productId: number;
  unitPrice: string;
  effectiveStartDate: string;
  effectiveEndDate: string | null;
}

export interface TransactionHistoryItem {
  type: string;
  documentNo: string;
  documentDate: string;
  amount: string;
  status: string;
}

export interface TransactionHistoryResponse {
  data: TransactionHistoryItem[];
  meta: { page: number; pageSize: number; totalCount: number };
}

// ------------------------------------------------------------
// 伝票共通（見積〜支払）
// ------------------------------------------------------------
export interface LineBase {
  id: number;
  lineNo: number;
  productId?: number;
  quantity?: string;
  unitPrice?: string;
  amount: string;
}

export interface QuotationLineOut extends LineBase {
  quotationId: number;
  productId: number;
  quantity: string;
  unitPrice: string;
}

export interface QuotationLineWithRemainingOut extends QuotationLineOut {
  orderedQty: string;
  remainingQty: string;
}

export interface QuotationOut {
  id: number;
  quotationNo: string;
  partnerId: number;
  quotationDate: string;
  expiryDate: string | null;
  conditionText: string | null;
  approvalStatus: ApprovalStatus;
  approvedBy: number | null;
  approvedAt: string | null;
}

export interface QuotationDetailOut extends QuotationOut {
  lines: QuotationLineOut[];
}

export interface OrderLineOut extends LineBase {
  orderId: number;
  quotationLineId: number | null;
  productId: number;
  quantity: string;
  unitPrice: string;
}

export interface OrderLineWithRemainingOut extends OrderLineOut {
  purchaseOrderedQty: string;
  remainingQtyForPurchase: string;
  soldQty: string;
  remainingQtyForSales: string;
}

export interface OrderOut {
  id: number;
  orderNo: string;
  partnerId: number;
  orderDate: string;
  status: DocumentStatus;
}

export interface OrderDetailOut extends OrderOut {
  lines: OrderLineOut[];
}

export interface PurchaseOrderLineOut extends LineBase {
  purchaseOrderId: number;
  orderLineId: number | null;
  productId: number;
  quantity: string;
  unitPrice: string;
}

export interface PurchaseOrderLineWithRemainingOut extends PurchaseOrderLineOut {
  purchasedQty: string;
  remainingQty: string;
}

export interface PurchaseOrderOut {
  id: number;
  purchaseOrderNo: string;
  partnerId: number;
  orderDate: string;
  status: DocumentStatus;
}

export interface PurchaseOrderDetailOut extends PurchaseOrderOut {
  lines: PurchaseOrderLineOut[];
}

export interface PurchaseLineOut extends LineBase {
  purchaseId: number;
  purchaseOrderLineId: number | null;
  productId: number;
  quantity: string;
  unitPrice: string;
}

export interface PurchaseOut {
  id: number;
  purchaseNo: string;
  partnerId: number;
  purchaseDate: string;
  status: DocumentStatus;
}

export interface PurchaseDetailOut extends PurchaseOut {
  lines: PurchaseLineOut[];
}

export interface SalesLineOut extends LineBase {
  salesId: number;
  orderLineId: number | null;
  productId: number;
  quantity: string;
  unitPrice: string;
}

export interface SalesOut {
  id: number;
  salesNo: string;
  partnerId: number;
  salesDate: string;
  status: DocumentStatus;
}

export interface SalesDetailOut extends SalesOut {
  lines: SalesLineOut[];
}

export interface ReceiptLineOut extends LineBase {
  receiptId: number;
  salesLineId: number | null;
}

export interface ReceiptOut {
  id: number;
  receiptNo: string;
  partnerId: number;
  receiptDate: string;
  paymentMethod: string | null;
  status: DocumentStatus;
}

export interface ReceiptDetailOut extends ReceiptOut {
  lines: ReceiptLineOut[];
}

export interface PaymentLineOut extends LineBase {
  paymentId: number;
  purchaseLineId: number | null;
}

export interface PaymentOut {
  id: number;
  paymentNo: string;
  partnerId: number;
  paymentDate: string;
  paymentMethod: string | null;
  status: DocumentStatus;
}

export interface PaymentDetailOut extends PaymentOut {
  lines: PaymentLineOut[];
}

export interface InventoryStockOut {
  productId: number;
  warehouseId: number;
  quantityOnHand: string;
}

export interface InventoryAllocationOut {
  id: number;
  allocationStage: AllocationStage;
  quotationLineId: number | null;
  orderLineId: number | null;
  salesLineId: number | null;
  productId: number;
  warehouseId: number | null;
  quantity: string;
}

export interface CurrentUser {
  email: string;
  name: string | null;
}
