"""DBアクセス層。

伝票（見積/受注/発注/仕入/売上/入金/支払）は「ヘッダ＋明細、上位明細への任意連携」という
共通パターンを持つため、DocumentCRUD にまとめて重複を避ける。
取引先・商品・単価はそれぞれ固有のロジック（属性の時系列管理等）を持つため個別に実装する。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models

HeaderT = TypeVar("HeaderT")
LineT = TypeVar("LineT")


# ------------------------------------------------------------
# コード自動採番
# ------------------------------------------------------------
def next_sequential_code(db: Session, model: type, code_column) -> str:
    """空欄で登録された場合のコード自動採番。

    「純粋な6桁数字」のコードだけを対象に最大値を求め+1する
    （手入力の任意コードと衝突しないようにするため）。
    """
    codes = db.execute(select(code_column).where(code_column.op("~")("^[0-9]{6}$"))).scalars().all()
    numbers = [int(c) for c in codes]
    next_n = (max(numbers) + 1) if numbers else 1
    return f"{next_n:06d}"


# ------------------------------------------------------------
# 表示名解決（取引先コード/名称・商品コード/名称・倉庫コード/名称）
# ------------------------------------------------------------
def _partner_lookup(db: Session, ids: set[int]) -> dict[int, models.Partner]:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = db.execute(
        select(models.Partner).options(selectinload(models.Partner.details)).where(models.Partner.id.in_(ids))
    ).scalars().all()
    return {p.id: p for p in rows}


def _product_lookup(db: Session, ids: set[int]) -> dict[int, models.Product]:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = db.execute(select(models.Product).where(models.Product.id.in_(ids))).scalars().all()
    return {p.id: p for p in rows}


def _warehouse_lookup(db: Session, ids: set[int]) -> dict[int, models.Warehouse]:
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    rows = db.execute(select(models.Warehouse).where(models.Warehouse.id.in_(ids))).scalars().all()
    return {w.id: w for w in rows}


def attach_partner_names(db: Session, objs: list[Any]) -> None:
    partners = _partner_lookup(db, {o.partner_id for o in objs if getattr(o, "partner_id", None)})
    for o in objs:
        p = partners.get(getattr(o, "partner_id", None))
        o.partner_code = p.partner_code if p else None  # type: ignore[attr-defined]
        o.partner_name = (p.current_detail.name if p and p.current_detail else None)  # type: ignore[attr-defined]


def attach_product_names(db: Session, objs: list[Any]) -> None:
    products = _product_lookup(db, {o.product_id for o in objs if getattr(o, "product_id", None)})
    for o in objs:
        p = products.get(getattr(o, "product_id", None))
        o.product_code = p.product_code if p else None  # type: ignore[attr-defined]
        o.product_name = p.name if p else None  # type: ignore[attr-defined]


def attach_warehouse_names(db: Session, objs: list[Any]) -> None:
    warehouses = _warehouse_lookup(db, {o.warehouse_id for o in objs if getattr(o, "warehouse_id", None)})
    for o in objs:
        w = warehouses.get(getattr(o, "warehouse_id", None))
        o.warehouse_code = w.warehouse_code if w else None  # type: ignore[attr-defined]
        o.warehouse_name = w.name if w else None  # type: ignore[attr-defined]


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
    db: Session, *, partner_code: str | None, partner_type: str, detail: dict[str, Any], created_by: int | None
) -> models.Partner:
    code = partner_code or next_sequential_code(db, models.Partner, models.Partner.partner_code)
    partner = models.Partner(partner_code=code, partner_type=partner_type, created_by=created_by)
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
    data = dict(data)
    if not data.get("product_code"):
        data["product_code"] = next_sequential_code(db, models.Product, models.Product.product_code)
    product = models.Product(**data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: models.Product, data: dict[str, Any]) -> models.Product:
    data = dict(data)
    if not data.get("product_code"):
        data.pop("product_code", None)  # 空欄なら既存コードを維持する
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
    limit: int = 200,
    offset: int = 0,
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
    stmt = stmt.order_by(models.PriceMaster.id.desc()).offset(offset).limit(limit)
    rows = list(db.execute(stmt).scalars().all())
    attach_partner_names(db, rows)
    attach_product_names(db, rows)
    return rows


def get_price_master(db: Session, price_id: int) -> models.PriceMaster | None:
    row = db.get(models.PriceMaster, price_id)
    if row is None:
        return None
    attach_partner_names(db, [row])
    attach_product_names(db, [row])
    return row


def create_price_master(db: Session, data: dict[str, Any]) -> models.PriceMaster:
    row = models.PriceMaster(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_price_master(db, row.id)  # type: ignore[return-value]


def update_price_master(db: Session, row: models.PriceMaster, data: dict[str, Any]) -> models.PriceMaster:
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return get_price_master(db, row.id)  # type: ignore[return-value]


def list_warehouses(db: Session) -> list[models.Warehouse]:
    return list(db.execute(select(models.Warehouse).order_by(models.Warehouse.id)).scalars().all())


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
    date_field: str  # 例: "quotation_date"
    status_field: str  # 例: "status" or "approval_status"
    lines_have_qty: bool = True  # False の場合は明細が金額のみ（入金/支払）

    def list(
        self,
        db: Session,
        *,
        partner_id: int | None = None,
        keyword: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HeaderT]:
        stmt = select(self.header_model)
        if partner_id is not None:
            stmt = stmt.where(self.header_model.partner_id == partner_id)  # type: ignore[attr-defined]
        if keyword:
            no_col = getattr(self.header_model, self.no_field)
            stmt = stmt.where(no_col.ilike(f"%{keyword}%"))
        date_col = getattr(self.header_model, self.date_field)
        if date_from is not None:
            stmt = stmt.where(date_col >= date_from)
        if date_to is not None:
            stmt = stmt.where(date_col <= date_to)
        if status:
            status_col = getattr(self.header_model, self.status_field)
            stmt = stmt.where(status_col == status)
        stmt = stmt.order_by(self.header_model.id.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
        items = list(db.execute(stmt).scalars().all())
        attach_partner_names(db, items)
        return items

    def get(self, db: Session, document_id: int) -> HeaderT | None:
        stmt = (
            select(self.header_model)
            .options(selectinload(getattr(self.header_model, self.lines_relationship)))
            .where(self.header_model.id == document_id)  # type: ignore[attr-defined]
        )
        obj = db.execute(stmt).scalar_one_or_none()
        if obj is None:
            return None
        attach_partner_names(db, [obj])
        lines = getattr(obj, self.lines_relationship)
        if self.lines_have_qty:
            attach_product_names(db, lines)
        return obj

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

    def update(
        self, db: Session, document_id: int, header_data: dict[str, Any], lines_data: list[dict[str, Any]] | None
    ) -> HeaderT | None:
        header = db.get(self.header_model, document_id)
        if header is None:
            return None
        for key, value in header_data.items():
            setattr(header, key, value)

        if lines_data:
            existing_lines = {line.id: line for line in getattr(header, self.lines_relationship)}
            for line_patch in lines_data:
                line_patch = dict(line_patch)
                line_id = line_patch.pop("id")
                line = existing_lines.get(line_id)
                if line is None:
                    raise ValueError(f"line {line_id} does not belong to this document")
                for key, value in line_patch.items():
                    setattr(line, key, value)
                if self.lines_have_qty and ("quantity" in line_patch or "unit_price" in line_patch):
                    line.amount = line.quantity * line.unit_price

        db.commit()
        return self.get(db, document_id)

    def _next_no(self, db: Session) -> str:
        # 純粋な連番採番の商品/取引先コードと同様に、既存の伝票番号の最大値+1を使う。
        no_col = getattr(self.header_model, self.no_field)
        pattern = f"^{self.no_prefix}[0-9]{{6}}$"
        codes = db.execute(select(no_col).where(no_col.op("~")(pattern))).scalars().all()
        numbers = [int(c[len(self.no_prefix):]) for c in codes]
        next_n = (max(numbers) + 1) if numbers else 1
        return f"{self.no_prefix}{next_n:06d}"


quotation_crud: DocumentCRUD[models.Quotation, models.QuotationLine] = DocumentCRUD(
    models.Quotation, models.QuotationLine, "quotation_id", "quotation_no", "Q", "lines",
    date_field="quotation_date", status_field="approval_status",
)
order_crud: DocumentCRUD[models.Order, models.OrderLine] = DocumentCRUD(
    models.Order, models.OrderLine, "order_id", "order_no", "SO", "lines",
    date_field="order_date", status_field="status",
)
purchase_order_crud: DocumentCRUD[models.PurchaseOrder, models.PurchaseOrderLine] = DocumentCRUD(
    models.PurchaseOrder, models.PurchaseOrderLine, "purchase_order_id", "purchase_order_no", "PO", "lines",
    date_field="order_date", status_field="status",
)
purchase_crud: DocumentCRUD[models.Purchase, models.PurchaseLine] = DocumentCRUD(
    models.Purchase, models.PurchaseLine, "purchase_id", "purchase_no", "PU", "lines",
    date_field="purchase_date", status_field="status",
)
sales_crud: DocumentCRUD[models.Sales, models.SalesLine] = DocumentCRUD(
    models.Sales, models.SalesLine, "sales_id", "sales_no", "SA", "lines",
    date_field="sales_date", status_field="status",
)
receipt_crud: DocumentCRUD[models.Receipt, models.ReceiptLine] = DocumentCRUD(
    models.Receipt, models.ReceiptLine, "receipt_id", "receipt_no", "RC", "lines",
    date_field="receipt_date", status_field="status", lines_have_qty=False,
)
payment_crud: DocumentCRUD[models.Payment, models.PaymentLine] = DocumentCRUD(
    models.Payment, models.PaymentLine, "payment_id", "payment_no", "PM", "lines",
    date_field="payment_date", status_field="status", lines_have_qty=False,
)


# ------------------------------------------------------------
# 残数（v_*_remaining ビュー参照）
# ------------------------------------------------------------
def quotation_lines_with_remaining(db: Session, quotation_id: int) -> list[dict]:
    lines = db.execute(
        select(models.QuotationLine).where(models.QuotationLine.quotation_id == quotation_id).order_by(models.QuotationLine.line_no)
    ).scalars().all()
    attach_product_names(db, lines)
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
                "product_code": line.product_code,  # type: ignore[attr-defined]
                "product_name": line.product_name,  # type: ignore[attr-defined]
                "ordered_qty": r.ordered_qty if r else 0,
                "remaining_qty": r.remaining_qty if r else line.quantity,
            }
        )
    return out


def order_lines_with_remaining(db: Session, order_id: int) -> list[dict]:
    lines = db.execute(
        select(models.OrderLine).where(models.OrderLine.order_id == order_id).order_by(models.OrderLine.line_no)
    ).scalars().all()
    attach_product_names(db, lines)
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
                "product_code": line.product_code,  # type: ignore[attr-defined]
                "product_name": line.product_name,  # type: ignore[attr-defined]
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
    attach_product_names(db, lines)
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
                "product_code": line.product_code,  # type: ignore[attr-defined]
                "product_name": line.product_name,  # type: ignore[attr-defined]
                "purchased_qty": r.purchased_qty if r else 0,
                "remaining_qty": r.remaining_qty if r else line.quantity,
            }
        )
    return out


def _row_to_dict(row: Any) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}
