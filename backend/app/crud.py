"""DBアクセス層。

伝票（見積/受注/発注/仕入/売上/入金/支払）は「ヘッダ＋明細、上位明細への任意連携」という
共通パターンを持つため、DocumentCRUD にまとめて重複を避ける。
取引先・商品・単価はそれぞれ固有のロジック（属性の時系列管理等）を持つため個別に実装する。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import models

HeaderT = TypeVar("HeaderT")
LineT = TypeVar("LineT")


# ------------------------------------------------------------
# 取引先
# ------------------------------------------------------------
def list_partners(
    db: Session, *, partner_type: str | None = None, keyword: str | None = None, limit: int = 50, offset: int = 0
) -> list[models.Partner]:
    stmt = select(models.Partner).options(selectinload(models.Partner.details))
    if partner_type is not None:
        stmt = stmt.where(models.Partner.partner_type == partner_type)
    if keyword:
        # 会社名はpartner_details側にあるため、現在値を含む簡易な部分一致検索を行う。
        stmt = stmt.join(models.PartnerDetail).where(
            (models.Partner.partner_code.ilike(f"%{keyword}%")) | (models.PartnerDetail.name.ilike(f"%{keyword}%"))
        )
    stmt = stmt.order_by(models.Partner.id.desc()).distinct().offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_partner(db: Session, partner_id: int) -> models.Partner | None:
    stmt = (
        select(models.Partner)
        .options(selectinload(models.Partner.details))
        .where(models.Partner.id == partner_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def create_partner(
    db: Session, *, partner_code: str, partner_type: str, detail: dict[str, Any], created_by: int | None
) -> models.Partner:
    partner = models.Partner(partner_code=partner_code, partner_type=partner_type, created_by=created_by)
    db.add(partner)
    db.flush()
    db.add(models.PartnerDetail(partner_id=partner.id, created_by=created_by, **detail))
    db.commit()
    db.refresh(partner)
    return get_partner(db, partner.id)  # type: ignore[return-value]


def add_partner_detail(
    db: Session, partner_id: int, detail: dict[str, Any], created_by: int | None
) -> models.PartnerDetail:
    row = models.PartnerDetail(partner_id=partner_id, created_by=created_by, **detail)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_partner_details(db: Session, partner_id: int) -> list[models.PartnerDetail]:
    stmt = (
        select(models.PartnerDetail)
        .where(models.PartnerDetail.partner_id == partner_id)
        .order_by(models.PartnerDetail.effective_date.desc(), models.PartnerDetail.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update_partner_flags(db: Session, partner: models.Partner, *, partner_type: str | None, is_active: bool | None) -> models.Partner:
    if partner_type is not None:
        partner.partner_type = partner_type
    if is_active is not None:
        partner.is_active = is_active
    db.commit()
    db.refresh(partner)
    return partner


def partner_transactions(db: Session, partner_id: int, *, types: list[str] | None = None) -> list[dict]:
    """見積/受注/発注/仕入/売上/入金/支払を横断して取引履歴として一覧化する。"""
    sources: list[tuple[str, type, str, str, str, str]] = [
        ("quotation", models.Quotation, "quotation_no", "quotation_date", "approval_status", "quotation_lines"),
        ("order", models.Order, "order_no", "order_date", "status", "order_lines"),
        ("purchase_order", models.PurchaseOrder, "purchase_order_no", "order_date", "status", "purchase_order_lines"),
        ("purchase", models.Purchase, "purchase_no", "purchase_date", "status", "purchase_lines"),
        ("sales", models.Sales, "sales_no", "sales_date", "status", "sales_lines"),
        ("receipt", models.Receipt, "receipt_no", "receipt_date", "status", "receipt_lines"),
        ("payment", models.Payment, "payment_no", "payment_date", "status", "payment_lines"),
    ]
    results: list[dict] = []
    for type_name, model, no_field, date_field, status_field, _ in sources:
        if types and type_name not in types:
            continue
        rows = db.execute(select(model).where(model.partner_id == partner_id)).scalars().all()
        for row in rows:
            amount = sum((line.amount for line in row.lines), start=type(row.lines[0].amount)(0)) if row.lines else 0
            results.append(
                {
                    "type": type_name,
                    "document_no": getattr(row, no_field),
                    "document_date": getattr(row, date_field),
                    "amount": amount,
                    "status": str(getattr(row, status_field).value if hasattr(getattr(row, status_field), "value") else getattr(row, status_field)),
                }
            )
    results.sort(key=lambda r: r["document_date"], reverse=True)
    return results


# ------------------------------------------------------------
# 商品 / 単価
# ------------------------------------------------------------
def list_products(db: Session, *, keyword: str | None = None, limit: int = 50, offset: int = 0) -> list[models.Product]:
    stmt = select(models.Product)
    if keyword:
        stmt = stmt.where((models.Product.product_code.ilike(f"%{keyword}%")) | (models.Product.name.ilike(f"%{keyword}%")))
    stmt = stmt.order_by(models.Product.id.desc()).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.get(models.Product, product_id)


def create_product(db: Session, data: dict[str, Any]) -> models.Product:
    product = models.Product(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: models.Product, data: dict[str, Any]) -> models.Product:
    for key, value in data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def list_price_master(
    db: Session,
    *,
    price_type: str | None = None,
    partner_id: int | None = None,
    product_id: int | None = None,
    as_of: date | None = None,
) -> list[models.PriceMaster]:
    stmt = select(models.PriceMaster)
    if price_type is not None:
        stmt = stmt.where(models.PriceMaster.price_type == price_type)
    if partner_id is not None:
        stmt = stmt.where(models.PriceMaster.partner_id == partner_id)
    if product_id is not None:
        stmt = stmt.where(models.PriceMaster.product_id == product_id)
    if as_of is not None:
        stmt = stmt.where(models.PriceMaster.effective_start_date <= as_of).where(
            (models.PriceMaster.effective_end_date.is_(None)) | (models.PriceMaster.effective_end_date >= as_of)
        )
    stmt = stmt.order_by(models.PriceMaster.effective_start_date.desc())
    return list(db.execute(stmt).scalars().all())


def create_price_master(db: Session, data: dict[str, Any]) -> models.PriceMaster:
    row = models.PriceMaster(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ------------------------------------------------------------
# 伝票チェーン共通（見積/受注/発注/仕入/売上/入金/支払）
# ------------------------------------------------------------
@dataclass
class DocumentCRUD(Generic[HeaderT, LineT]):
    header_model: type[HeaderT]
    line_model: type[LineT]
    line_fk_name: str  # 例: "quotation_id"
    no_field: str  # 例: "quotation_no"
    no_prefix: str  # 採番プレフィックス。例: "Q"
    lines_relationship: str  # 例: "lines"

    def list(self, db: Session, *, partner_id: int | None = None, limit: int = 50, offset: int = 0) -> list[HeaderT]:
        stmt = select(self.header_model)
        if partner_id is not None:
            stmt = stmt.where(self.header_model.partner_id == partner_id)  # type: ignore[attr-defined]
        stmt = stmt.order_by(self.header_model.id.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
        return list(db.execute(stmt).scalars().all())

    def get(self, db: Session, document_id: int) -> HeaderT | None:
        stmt = (
            select(self.header_model)
            .options(selectinload(getattr(self.header_model, self.lines_relationship)))
            .where(self.header_model.id == document_id)  # type: ignore[attr-defined]
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, header_data: dict[str, Any], lines_data: list[dict[str, Any]], created_by: int | None) -> HeaderT:
        doc_no = self._next_no(db)
        header_kwargs = dict(header_data)
        if hasattr(self.header_model, "created_by"):
            header_kwargs["created_by"] = created_by
        header = self.header_model(**header_kwargs, **{self.no_field: doc_no})  # type: ignore[call-arg]
        db.add(header)
        db.flush()  # header.id を確定させる
        for i, line in enumerate(lines_data, start=1):
            db.add(self.line_model(**{self.line_fk_name: header.id, "line_no": i}, **line))  # type: ignore[call-arg]
        db.commit()
        return self.get(db, header.id)  # type: ignore[attr-defined,arg-type]

    def _next_no(self, db: Session) -> str:
        # 簡易な連番採番。本番運用では専用の採番テーブル or DBシーケンス + アドバイザリロックで
        # 同時実行時の重複を防ぐこと（現状は同時作成でのレース条件がある）。
        count = db.execute(select(func.count()).select_from(self.header_model)).scalar_one()
        return f"{self.no_prefix}{count + 1:06d}"


def line_amount(quantity: Any, unit_price: Any) -> Any:
    return quantity * unit_price


quotation_crud: DocumentCRUD[models.Quotation, models.QuotationLine] = DocumentCRUD(
    models.Quotation, models.QuotationLine, "quotation_id", "quotation_no", "Q", "lines"
)
order_crud: DocumentCRUD[models.Order, models.OrderLine] = DocumentCRUD(
    models.Order, models.OrderLine, "order_id", "order_no", "SO", "lines"
)
purchase_order_crud: DocumentCRUD[models.PurchaseOrder, models.PurchaseOrderLine] = DocumentCRUD(
    models.PurchaseOrder, models.PurchaseOrderLine, "purchase_order_id", "purchase_order_no", "PO", "lines"
)
purchase_crud: DocumentCRUD[models.Purchase, models.PurchaseLine] = DocumentCRUD(
    models.Purchase, models.PurchaseLine, "purchase_id", "purchase_no", "PU", "lines"
)
sales_crud: DocumentCRUD[models.Sales, models.SalesLine] = DocumentCRUD(
    models.Sales, models.SalesLine, "sales_id", "sales_no", "SA", "lines"
)
receipt_crud: DocumentCRUD[models.Receipt, models.ReceiptLine] = DocumentCRUD(
    models.Receipt, models.ReceiptLine, "receipt_id", "receipt_no", "RC", "lines"
)
payment_crud: DocumentCRUD[models.Payment, models.PaymentLine] = DocumentCRUD(
    models.Payment, models.PaymentLine, "payment_id", "payment_no", "PM", "lines"
)


# ------------------------------------------------------------
# 残数（v_*_remaining ビュー参照）
# ------------------------------------------------------------
def quotation_lines_with_remaining(db: Session, quotation_id: int) -> list[dict]:
    lines = db.execute(
        select(models.QuotationLine).where(models.QuotationLine.quotation_id == quotation_id).order_by(models.QuotationLine.line_no)
    ).scalars().all()
    remaining = {
        r.quotation_line_id: r
        for r in db.execute(
            select(models.QuotationRemaining).where(models.QuotationRemaining.quotation_id == quotation_id)
        ).scalars()
    }
    out = []
    for line in lines:
        r = remaining.get(line.id)
        out.append(
            {
                **_row_to_dict(line),
                "ordered_qty": r.ordered_qty if r else 0,
                "remaining_qty": r.remaining_qty if r else line.quantity,
            }
        )
    return out


def order_lines_with_remaining(db: Session, order_id: int) -> list[dict]:
    lines = db.execute(
        select(models.OrderLine).where(models.OrderLine.order_id == order_id).order_by(models.OrderLine.line_no)
    ).scalars().all()
    purchase_remaining = {
        r.order_line_id: r
        for r in db.execute(
            select(models.OrderRemainingForPurchase).where(models.OrderRemainingForPurchase.order_id == order_id)
        ).scalars()
    }
    sales_remaining = {
        r.order_line_id: r
        for r in db.execute(
            select(models.OrderRemainingForSales).where(models.OrderRemainingForSales.order_id == order_id)
        ).scalars()
    }
    out = []
    for line in lines:
        pr = purchase_remaining.get(line.id)
        sr = sales_remaining.get(line.id)
        out.append(
            {
                **_row_to_dict(line),
                "purchase_ordered_qty": pr.purchase_ordered_qty if pr else 0,
                "remaining_qty_for_purchase": pr.remaining_qty if pr else line.quantity,
                "sold_qty": sr.sold_qty if sr else 0,
                "remaining_qty_for_sales": sr.remaining_qty if sr else line.quantity,
            }
        )
    return out


def purchase_order_lines_with_remaining(db: Session, purchase_order_id: int) -> list[dict]:
    lines = db.execute(
        select(models.PurchaseOrderLine)
        .where(models.PurchaseOrderLine.purchase_order_id == purchase_order_id)
        .order_by(models.PurchaseOrderLine.line_no)
    ).scalars().all()
    remaining = {
        r.purchase_order_line_id: r
        for r in db.execute(
            select(models.PurchaseOrderRemaining).where(
                models.PurchaseOrderRemaining.purchase_order_id == purchase_order_id
            )
        ).scalars()
    }
    out = []
    for line in lines:
        r = remaining.get(line.id)
        out.append(
            {
                **_row_to_dict(line),
                "purchased_qty": r.purchased_qty if r else 0,
                "remaining_qty": r.remaining_qty if r else line.quantity,
            }
        )
    return out


def _row_to_dict(row: Any) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}
