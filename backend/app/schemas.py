"""Pydantic スキーマ。api/openapi.yaml のフィールド名（camelCase）と対応させる。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .models import ApprovalStatus, DocumentStatus, PartnerType, PriceType, RoundingType, UserRole, UserStatus


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ------------------------------------------------------------
# 認証 / ユーザー管理
# ------------------------------------------------------------
class CurrentUser(CamelModel):
    email: str
    name: str | None = None
    role: UserRole


class AdminUserOut(CamelModel):
    id: int
    employee_code: str
    name: str
    email: str
    role: UserRole
    status: UserStatus
    created_at: datetime


# ------------------------------------------------------------
# 共通マスタ: 取引先
# ------------------------------------------------------------
class PartnerDetailIn(CamelModel):
    effective_date: date
    name: str
    name_kana: str | None = None
    representative_name: str | None = None
    postal_code: str | None = None
    address: str | None = None
    phone: str | None = None
    fax: str | None = None
    email: str | None = None
    contact_person: str | None = None
    credit_limit: Decimal | None = None
    remarks: str | None = None


class PartnerDetailOut(PartnerDetailIn):
    id: int
    partner_id: int
    created_at: datetime


class PartnerOut(CamelModel):
    id: int
    partner_code: str
    partner_type: PartnerType
    rounding_type: RoundingType
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerWithCurrentDetailOut(PartnerOut):
    current_detail: PartnerDetailOut | None = None


class PartnerCreateRequest(CamelModel):
    partner_code: str | None = None  # 空欄なら自動採番（6桁ゼロサプレス）
    partner_type: PartnerType
    rounding_type: RoundingType = RoundingType.round
    detail: PartnerDetailIn


class PartnerPatchRequest(CamelModel):
    partner_type: PartnerType | None = None
    rounding_type: RoundingType | None = None
    is_active: bool | None = None


class TransactionHistoryItem(CamelModel):
    type: str
    document_no: str
    document_date: date
    amount: Decimal
    status: str


class PageMeta(CamelModel):
    page: int
    page_size: int
    total_count: int


class TransactionHistoryResponse(CamelModel):
    data: list[TransactionHistoryItem]
    meta: PageMeta


# ------------------------------------------------------------
# 共通マスタ: 商品 / 単価
# ------------------------------------------------------------
class ProductIn(CamelModel):
    product_code: str | None = None  # 空欄なら自動採番（6桁ゼロサプレス）
    name: str
    category: str | None = None
    unit: str
    default_supplier_id: int | None = None
    is_active: bool = True


class ProductOut(CamelModel):
    id: int
    product_code: str
    name: str
    category: str | None = None
    unit: str
    default_supplier_id: int | None = None
    is_active: bool = True


class WarehouseOut(CamelModel):
    id: int
    warehouse_code: str
    name: str


class PriceMasterIn(CamelModel):
    price_type: PriceType
    partner_id: int | None = None
    product_id: int
    unit_price: Decimal
    effective_start_date: date
    effective_end_date: date | None = None


class PriceMasterPatch(CamelModel):
    price_type: PriceType | None = None
    partner_id: int | None = None
    product_id: int | None = None
    unit_price: Decimal | None = None
    effective_start_date: date | None = None
    effective_end_date: date | None = None


class PriceMasterOut(PriceMasterIn):
    id: int
    partner_code: str | None = None
    partner_name: str | None = None
    product_code: str | None = None
    product_name: str | None = None


# ------------------------------------------------------------
# 見積
# ------------------------------------------------------------
class QuotationLineIn(CamelModel):
    product_id: int
    # 数量・単価が両方揃っていればamountは自動計算されるため送信不要。
    # どちらか一方でも未入力の場合のみ amount を直接指定する。
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class QuotationLineOut(QuotationLineIn):
    id: int
    quotation_id: int
    line_no: int
    amount: Decimal
    rounding_type: RoundingType
    product_code: str | None = None
    product_name: str | None = None


class QuotationLineWithRemainingOut(QuotationLineOut):
    ordered_qty: Decimal = Decimal(0)
    remaining_qty: Decimal = Decimal(0)


class QuotationIn(CamelModel):
    partner_id: int
    quotation_date: date
    expiry_date: date | None = None
    condition_text: str | None = None
    lines: list[QuotationLineIn]


class QuotationOut(CamelModel):
    id: int
    quotation_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    quotation_date: date
    expiry_date: date | None = None
    condition_text: str | None = None
    approval_status: ApprovalStatus
    approved_by: int | None = None
    approved_at: datetime | None = None


class QuotationDetailOut(QuotationOut):
    lines: list[QuotationLineOut]


class QuotationLineSelection(CamelModel):
    quotation_line_id: int
    quantity: Decimal | None = None


class QuotationConfirmOrdersRequest(CamelModel):
    mode: str  # "whole_document" | "selected_lines"
    line_selections: list[QuotationLineSelection] = []


# ------------------------------------------------------------
# 伝票明細の修正（編集）用共通スキーマ
# 既存明細の productId/quantity/unitPrice、または amount のみを更新できる。
# 明細の追加・削除には対応していない（id で既存明細を指定する）。
# ------------------------------------------------------------
class ProductLinePatch(CamelModel):
    id: int
    product_id: int | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class AmountLinePatch(CamelModel):
    id: int
    amount: Decimal | None = None


class QuotationPatch(CamelModel):
    partner_id: int | None = None
    quotation_date: date | None = None
    expiry_date: date | None = None
    condition_text: str | None = None
    lines: list[ProductLinePatch] | None = None


# ------------------------------------------------------------
# 受注
# ------------------------------------------------------------
class OrderLineIn(CamelModel):
    quotation_line_id: int | None = None
    product_id: int
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class OrderLineOut(OrderLineIn):
    id: int
    order_id: int
    line_no: int
    amount: Decimal
    rounding_type: RoundingType
    product_code: str | None = None
    product_name: str | None = None


class OrderLineWithRemainingOut(OrderLineOut):
    purchase_ordered_qty: Decimal = Decimal(0)
    remaining_qty_for_purchase: Decimal = Decimal(0)
    sold_qty: Decimal = Decimal(0)
    remaining_qty_for_sales: Decimal = Decimal(0)


class OrderIn(CamelModel):
    partner_id: int
    order_date: date
    lines: list[OrderLineIn]


class OrderOut(CamelModel):
    id: int
    order_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    order_date: date
    status: DocumentStatus


class OrderDetailOut(OrderOut):
    lines: list[OrderLineOut]


class OrderPatch(CamelModel):
    partner_id: int | None = None
    order_date: date | None = None
    status: DocumentStatus | None = None
    lines: list[ProductLinePatch] | None = None


# ------------------------------------------------------------
# 発注
# ------------------------------------------------------------
class PurchaseOrderLineIn(CamelModel):
    order_line_id: int | None = None
    product_id: int
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class PurchaseOrderLineOut(PurchaseOrderLineIn):
    id: int
    purchase_order_id: int
    line_no: int
    amount: Decimal
    rounding_type: RoundingType
    product_code: str | None = None
    product_name: str | None = None


class PurchaseOrderLineWithRemainingOut(PurchaseOrderLineOut):
    purchased_qty: Decimal = Decimal(0)
    remaining_qty: Decimal = Decimal(0)


class PurchaseOrderIn(CamelModel):
    partner_id: int
    order_date: date
    lines: list[PurchaseOrderLineIn]


class PurchaseOrderOut(CamelModel):
    id: int
    purchase_order_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    order_date: date
    status: DocumentStatus


class PurchaseOrderDetailOut(PurchaseOrderOut):
    lines: list[PurchaseOrderLineOut]


class PurchaseOrderPatch(CamelModel):
    partner_id: int | None = None
    order_date: date | None = None
    status: DocumentStatus | None = None
    lines: list[ProductLinePatch] | None = None


# ------------------------------------------------------------
# 仕入
# ------------------------------------------------------------
class PurchaseLineIn(CamelModel):
    purchase_order_line_id: int | None = None
    product_id: int
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class PurchaseLineOut(PurchaseLineIn):
    id: int
    purchase_id: int
    line_no: int
    amount: Decimal
    rounding_type: RoundingType
    product_code: str | None = None
    product_name: str | None = None


class PurchaseIn(CamelModel):
    partner_id: int
    purchase_date: date
    lines: list[PurchaseLineIn]


class PurchaseOut(CamelModel):
    id: int
    purchase_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    purchase_date: date
    status: DocumentStatus


class PurchaseDetailOut(PurchaseOut):
    lines: list[PurchaseLineOut]


class PurchasePatch(CamelModel):
    partner_id: int | None = None
    purchase_date: date | None = None
    status: DocumentStatus | None = None
    lines: list[ProductLinePatch] | None = None


# ------------------------------------------------------------
# 売上
# ------------------------------------------------------------
class SalesLineIn(CamelModel):
    order_line_id: int | None = None
    product_id: int
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class SalesLineOut(SalesLineIn):
    id: int
    sales_id: int
    line_no: int
    amount: Decimal
    rounding_type: RoundingType
    product_code: str | None = None
    product_name: str | None = None


class SalesIn(CamelModel):
    partner_id: int
    sales_date: date
    lines: list[SalesLineIn]


class SalesOut(CamelModel):
    id: int
    sales_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    sales_date: date
    status: DocumentStatus


class SalesDetailOut(SalesOut):
    lines: list[SalesLineOut]


class SalesPatch(CamelModel):
    partner_id: int | None = None
    sales_date: date | None = None
    status: DocumentStatus | None = None
    lines: list[ProductLinePatch] | None = None


# ------------------------------------------------------------
# 入金
# ------------------------------------------------------------
class ReceiptLineIn(CamelModel):
    sales_line_id: int | None = None
    amount: Decimal


class ReceiptLineOut(ReceiptLineIn):
    id: int
    receipt_id: int
    line_no: int


class ReceiptIn(CamelModel):
    partner_id: int
    receipt_date: date
    payment_method: str | None = None
    lines: list[ReceiptLineIn]


class ReceiptOut(CamelModel):
    id: int
    receipt_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    receipt_date: date
    payment_method: str | None = None
    status: DocumentStatus


class ReceiptDetailOut(ReceiptOut):
    lines: list[ReceiptLineOut]


class ReceiptPatch(CamelModel):
    partner_id: int | None = None
    receipt_date: date | None = None
    payment_method: str | None = None
    status: DocumentStatus | None = None
    lines: list[AmountLinePatch] | None = None


# ------------------------------------------------------------
# 支払
# ------------------------------------------------------------
class PaymentLineIn(CamelModel):
    purchase_line_id: int | None = None
    amount: Decimal


class PaymentLineOut(PaymentLineIn):
    id: int
    payment_id: int
    line_no: int


class PaymentIn(CamelModel):
    partner_id: int
    payment_date: date
    payment_method: str | None = None
    lines: list[PaymentLineIn]


class PaymentOut(CamelModel):
    id: int
    payment_no: str
    partner_id: int
    partner_code: str | None = None
    partner_name: str | None = None
    payment_date: date
    payment_method: str | None = None
    status: DocumentStatus


class PaymentDetailOut(PaymentOut):
    lines: list[PaymentLineOut]


class PaymentPatch(CamelModel):
    partner_id: int | None = None
    payment_date: date | None = None
    payment_method: str | None = None
    status: DocumentStatus | None = None
    lines: list[AmountLinePatch] | None = None


# ------------------------------------------------------------
# 在庫
# ------------------------------------------------------------
class InventoryStockOut(CamelModel):
    product_id: int
    product_code: str | None = None
    product_name: str | None = None
    warehouse_id: int
    warehouse_code: str | None = None
    warehouse_name: str | None = None
    quantity_on_hand: Decimal


class InventoryAllocationIn(CamelModel):
    allocation_stage: str
    quotation_line_id: int | None = None
    order_line_id: int | None = None
    sales_line_id: int | None = None
    product_id: int
    warehouse_id: int | None = None
    quantity: Decimal


class InventoryAllocationOut(InventoryAllocationIn):
    id: int
    product_code: str | None = None
    product_name: str | None = None
    warehouse_code: str | None = None
    warehouse_name: str | None = None
