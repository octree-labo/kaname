"""SQLAlchemy ORM モデル。

db/schema.sql に定義したテーブル/ビューと1対1で対応する。
テーブル自体は schema.sql を実行して作成する運用とし
（scripts/init_db.py 参照）、ここでは既存テーブルへのマッピングのみを行う
（ENUM型も schema.sql 側で CREATE TYPE 済みなので create_type=False）。
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------
# ENUM
# ------------------------------------------------------------
class PartnerType(str, enum.Enum):
    customer = "customer"
    supplier = "supplier"
    both = "both"


class ApprovalStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DocumentStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    cancelled = "cancelled"


class PriceType(str, enum.Enum):
    sales = "sales"
    purchase = "purchase"


class AllocationStage(str, enum.Enum):
    quotation = "quotation"
    order = "order"
    sales = "sales"


class UserRole(str, enum.Enum):
    owner = "owner"
    member = "member"


class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class RoundingType(str, enum.Enum):
    floor = "floor"  # 切り捨て
    ceil = "ceil"  # 切り上げ
    round = "round"  # 四捨五入


def _pg_enum(python_enum: type[enum.Enum], name: str) -> SAEnum:
    return SAEnum(
        python_enum,
        name=name,
        native_enum=True,
        create_type=False,
        values_callable=lambda e: [x.value for x in e],
    )


# ------------------------------------------------------------
# ユーザー
# ------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(_pg_enum(UserRole, "user_role"), nullable=False, default=UserRole.member)
    status: Mapped[UserStatus] = mapped_column(
        _pg_enum(UserStatus, "user_status"), nullable=False, default=UserStatus.pending
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------
# 共通マスタ: 取引先
# ------------------------------------------------------------
class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    partner_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    partner_type: Mapped[PartnerType] = mapped_column(_pg_enum(PartnerType, "partner_type"), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(
        _pg_enum(RoundingType, "rounding_type"), nullable=False, default=RoundingType.round
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    details: Mapped[list["PartnerDetail"]] = relationship(
        back_populates="partner", order_by="PartnerDetail.effective_date.desc()"
    )

    @property
    def current_detail(self) -> "PartnerDetail | None":
        today = date.today()
        candidates = [d for d in self.details if d.effective_date <= today]
        if not candidates:
            return None
        return max(candidates, key=lambda d: (d.effective_date, d.id))


class PartnerDetail(Base):
    """取引先の属性を有効日付きで積み上げる（SCD Type2）。

    現在値の取得は Partner.current_detail、または v_partner_current ビューを使う。
    行の積み重ね自体が変更履歴ログを兼ねる。
    """

    __tablename__ = "partner_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_kana: Mapped[str | None] = mapped_column(String(200))
    representative_name: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    address: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    fax: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    contact_person: Mapped[str | None] = mapped_column(String(100))
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["Partner"] = relationship(back_populates="details")


# ------------------------------------------------------------
# 共通マスタ: 商品 / 単価
# ------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    default_supplier_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("partners.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceMaster(Base):
    __tablename__ = "price_master"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    price_type: Mapped[PriceType] = mapped_column(_pg_enum(PriceType, "price_type"), nullable=False)
    partner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("partners.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------
# 倉庫 / 在庫
# ------------------------------------------------------------
class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class InventoryStock(Base):
    __tablename__ = "inventory_stocks"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("warehouses.id"), nullable=False)
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)


class InventoryAllocation(Base):
    __tablename__ = "inventory_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    allocation_stage: Mapped[AllocationStage] = mapped_column(
        _pg_enum(AllocationStage, "allocation_stage"), nullable=False
    )
    quotation_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("quotation_lines.id"))
    order_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("order_lines.id"))
    sales_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sales_lines.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("warehouses.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryMovement(Base):
    """在庫の受払（入庫はプラス、出庫はマイナス）。仕入・売上の確定/訂正/取消のたびに差分を記録する。"""

    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("warehouses.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    purchase_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("purchase_lines.id"))
    sales_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sales_lines.id"))
    migrated: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ------------------------------------------------------------
# 見積
# ------------------------------------------------------------
class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    quotation_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    condition_text: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        _pg_enum(ApprovalStatus, "approval_status"), nullable=False, default=ApprovalStatus.draft
    )
    approved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["QuotationLine"]] = relationship(
        back_populates="quotation", order_by="QuotationLine.line_no"
    )


class QuotationLine(Base):
    __tablename__ = "quotation_lines"
    __table_args__ = (UniqueConstraint("quotation_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quotations.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 0), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(_pg_enum(RoundingType, "rounding_type"), nullable=False)

    quotation: Mapped["Quotation"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 受注
# ------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["OrderLine"]] = relationship(back_populates="order", order_by="OrderLine.line_no")


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("order_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    quotation_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("quotation_lines.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 0), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(_pg_enum(RoundingType, "rounding_type"), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 発注
# ------------------------------------------------------------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_order_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order", order_by="PurchaseOrderLine.line_no"
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (UniqueConstraint("purchase_order_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("purchase_orders.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    order_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("order_lines.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 0), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(_pg_enum(RoundingType, "rounding_type"), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 仕入
# ------------------------------------------------------------
class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["PurchaseLine"]] = relationship(back_populates="purchase", order_by="PurchaseLine.line_no")


class PurchaseLine(Base):
    __tablename__ = "purchase_lines"
    __table_args__ = (UniqueConstraint("purchase_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("purchases.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    purchase_order_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("purchase_order_lines.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("warehouses.id"))  # 入庫する倉庫
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 0), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(_pg_enum(RoundingType, "rounding_type"), nullable=False)

    purchase: Mapped["Purchase"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 売上
# ------------------------------------------------------------
class Sales(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sales_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["SalesLine"]] = relationship(back_populates="sales", order_by="SalesLine.line_no")


class SalesLine(Base):
    __tablename__ = "sales_lines"
    __table_args__ = (UniqueConstraint("sales_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sales_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sales.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    order_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("order_lines.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("warehouses.id"))  # 出庫する倉庫
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 0), nullable=False)
    rounding_type: Mapped[RoundingType] = mapped_column(_pg_enum(RoundingType, "rounding_type"), nullable=False)

    sales: Mapped["Sales"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 入金
# ------------------------------------------------------------
class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["ReceiptLine"]] = relationship(back_populates="receipt", order_by="ReceiptLine.line_no")


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"
    __table_args__ = (UniqueConstraint("receipt_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("receipts.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    sales_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sales_lines.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

    receipt: Mapped["Receipt"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 支払
# ------------------------------------------------------------
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("partners.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[DocumentStatus] = mapped_column(
        _pg_enum(DocumentStatus, "document_status"), nullable=False, default=DocumentStatus.confirmed
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["PaymentLine"]] = relationship(back_populates="payment", order_by="PaymentLine.line_no")


class PaymentLine(Base):
    __tablename__ = "payment_lines"
    __table_args__ = (UniqueConstraint("payment_id", "line_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("payments.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    purchase_line_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("purchase_lines.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="lines")


# ------------------------------------------------------------
# 残数ビュー（読み取り専用マッピング。schema.sql の CREATE VIEW と対応）
# 各 *_line_id は真の主キーではないが、行を一意に識別できるため
# SQLAlchemy ORM 上は primary_key=True として扱う（更新は行わない）。
# ------------------------------------------------------------
class QuotationRemaining(Base):
    __tablename__ = "v_quotation_remaining"

    quotation_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(BigInteger)
    quoted_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class OrderRemainingForPurchase(Base):
    __tablename__ = "v_order_remaining_for_purchase"

    order_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    purchase_ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class OrderRemainingForSales(Base):
    __tablename__ = "v_order_remaining_for_sales"

    order_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    sold_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class PurchaseOrderRemaining(Base):
    __tablename__ = "v_purchase_order_remaining"

    purchase_order_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(BigInteger)
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    purchased_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class SalesRemainingForReceipt(Base):
    __tablename__ = "v_sales_remaining_for_receipt"

    sales_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sales_id: Mapped[int] = mapped_column(BigInteger)
    sales_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    received_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))


class PurchaseRemainingForPayment(Base):
    __tablename__ = "v_purchase_remaining_for_payment"

    purchase_line_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(BigInteger)
    purchase_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
