"""DBアクセス層。

伝票（見積/受注/発注/仕入/売上/入金/支払）は「ヘッダ＋明細、上位明細への任意連携」という
共通パターンを持つため、DocumentCRUD にまとめて重複を避ける。
取引先・商品・単価はそれぞれ固有のロジック（属性の時系列管理等）を持つため個別に実装する。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from . import models

HeaderT = TypeVar("HeaderT")
LineT = TypeVar("LineT")

_ROUNDING_MODES = {
    models.RoundingType.floor: ROUND_FLOOR,
    models.RoundingType.ceil: ROUND_CEILING,
    models.RoundingType.round: ROUND_HALF_UP,
}


def compute_amount(quantity: Decimal, unit_price: Decimal, rounding_type: models.RoundingType) -> Decimal:
    """数量×単価を、取引先の丸め区分に従って整数金額に丸める。"""
    raw = Decimal(quantity) * Decimal(unit_price)
    return raw.quantize(Decimal("1"), rounding=_ROUNDING_MODES[rounding_type])


def _to_integer_amount(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def resolve_line_amount(line: dict[str, Any], partner: models.Partner) -> dict[str, Any]:
    """明細1件分の amount/rounding_type を確定させる。

    数量・単価が両方揃っていれば取引先の丸め区分で自動計算し、その丸め区分を
    明細にスナップショットとして保存する（後で取引先マスタの丸め区分を
    変更しても、この明細の再計算には常にこの値が使われる）。
    どちらか一方でも未入力の場合は、明細に指定された amount をそのまま使う
    （整数に丸めて保存する）。
    """
    line = dict(line)
    quantity = line.get("quantity")
    unit_price = line.get("unit_price")
    if quantity is not None and unit_price is not None:
        line["amount"] = compute_amount(quantity, unit_price, partner.rounding_type)
    else:
        if line.get("amount") is None:
            raise ValueError("amount is required when quantity or unit_price is not provided")
        line["amount"] = _to_integer_amount(line["amount"])
    line["rounding_type"] = partner.rounding_type
    return line


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
    db: Session,
    *,
    partner_code: str | None,
    partner_type: str,
    rounding_type: str,
    detail: dict[str, Any],
    created_by: int | None,
) -> models.Partner:
    code = partner_code or next_sequential_code(db, models.Partner, models.Partner.partner_code)
    partner = models.Partner(
        partner_code=code, partner_type=partner_type, rounding_type=rounding_type, created_by=created_by
    )
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


def update_partner_flags(
    db: Session,
    partner: models.Partner,
    *,
    partner_type: str | None,
    rounding_type: str | None,
    is_active: bool | None,
) -> models.Partner:
    if partner_type is not None:
        partner.partner_type = partner_type
    if rounding_type is not None:
        partner.rounding_type = rounding_type
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
# ------------------------------------------------------------
# 在庫の受払（仕入で入庫、売上で出庫）
# ------------------------------------------------------------
def default_warehouse_id(db: Session) -> int:
    wid = db.execute(select(models.Warehouse.id).order_by(models.Warehouse.id).limit(1)).scalar_one_or_none()
    if wid is None:
        raise ValueError("倉庫が登録されていません。先に倉庫を登録してください")
    return wid


def fill_warehouse(db: Session, line: dict[str, Any]) -> dict[str, Any]:
    """明細の倉庫が空なら既定の倉庫を入れ、指定されていれば存在を確かめる。"""
    line = dict(line)
    if line.get("warehouse_id") is None:
        line["warehouse_id"] = default_warehouse_id(db)
    elif db.get(models.Warehouse, line["warehouse_id"]) is None:
        raise ValueError("指定した倉庫が見つかりません")
    return line


def _adjust_stock(db: Session, product_id: int, warehouse_id: int, delta: Decimal) -> None:
    """在庫数を delta だけ増減する（行がなければ作る）。同時に更新されても数がずれないよう DB 側で足し込む。"""
    stmt = pg_insert(models.InventoryStock).values(
        product_id=product_id, warehouse_id=warehouse_id, quantity_on_hand=delta
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["product_id", "warehouse_id"],
        set_={"quantity_on_hand": models.InventoryStock.quantity_on_hand + delta},
    )
    db.execute(stmt)


def sync_inventory_movements(db: Session, movement: str, header: Any, lines: list[Any]) -> None:
    """伝票の今の内容に合わせて、受払履歴と在庫数をそろえる。

    明細ごとに「あるべき受払（確定なら 数量×符号、下書き・取消なら 0）」と
    「これまでに記録した受払の合計」を商品×倉庫ごとに比べ、差分だけを新しい受払として記録し、
    同じ数だけ在庫数を増減する。登録・数量や倉庫の訂正・取消・取消の取り消しを、同じ処理で扱える。
    """
    sign = Decimal(1) if movement == "purchase" else Decimal(-1)
    m = models.InventoryMovement
    line_col = m.purchase_line_id if movement == "purchase" else m.sales_line_id
    line_key = "purchase_line_id" if movement == "purchase" else "sales_line_id"
    status = getattr(header.status, "value", header.status)

    line_ids = [line.id for line in lines]
    recorded: dict[int, dict[tuple[int, int], Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    if line_ids:
        for line_id, pid, wid, qty in db.execute(
            select(line_col, m.product_id, m.warehouse_id, m.quantity).where(line_col.in_(line_ids))
        ).all():
            recorded[line_id][(pid, wid)] += Decimal(qty)

    for line in lines:
        wanted: dict[tuple[int, int], Decimal] = {}
        if status == "confirmed" and line.quantity is not None and line.warehouse_id is not None:
            wanted[(line.product_id, line.warehouse_id)] = sign * Decimal(line.quantity)
        have = recorded.get(line.id, {})
        for key in set(wanted) | set(have):
            delta = wanted.get(key, Decimal(0)) - have.get(key, Decimal(0))
            if delta == 0:
                continue
            pid, wid = key
            db.add(m(product_id=pid, warehouse_id=wid, quantity=delta, movement_type=movement, **{line_key: line.id}))
            _adjust_stock(db, pid, wid, delta)


def list_inventory_movements(
    db: Session, *, product_id: int | None = None, warehouse_id: int | None = None, limit: int = 200
) -> list[dict]:
    m = models.InventoryMovement
    stmt = select(m)
    if product_id is not None:
        stmt = stmt.where(m.product_id == product_id)
    if warehouse_id is not None:
        stmt = stmt.where(m.warehouse_id == warehouse_id)
    rows = list(db.execute(stmt.order_by(m.id.desc()).limit(limit)).scalars().all())
    attach_product_names(db, rows)
    attach_warehouse_names(db, rows)

    docs: dict[tuple[str, int], tuple[int, str, date]] = {}
    for kind, line_m, head_m, fk, no, dt, ids in (
        ("purchase", models.PurchaseLine, models.Purchase, "purchase_id", "purchase_no", "purchase_date",
         {r.purchase_line_id for r in rows if r.purchase_line_id}),
        ("sales", models.SalesLine, models.Sales, "sales_id", "sales_no", "sales_date",
         {r.sales_line_id for r in rows if r.sales_line_id}),
    ):
        if not ids:
            continue
        for lid, hid, doc_no, doc_date in db.execute(
            select(line_m.id, head_m.id, getattr(head_m, no), getattr(head_m, dt))
            .join(head_m, head_m.id == getattr(line_m, fk))
            .where(line_m.id.in_(ids))
        ).all():
            docs[(kind, lid)] = (hid, doc_no, doc_date)

    out = []
    for r in rows:
        doc = docs.get((r.movement_type, r.purchase_line_id or r.sales_line_id))
        out.append({
            "id": r.id,
            "product_id": r.product_id,
            "product_code": r.product_code,  # type: ignore[attr-defined]
            "product_name": r.product_name,  # type: ignore[attr-defined]
            "warehouse_id": r.warehouse_id,
            "warehouse_code": r.warehouse_code,  # type: ignore[attr-defined]
            "warehouse_name": r.warehouse_name,  # type: ignore[attr-defined]
            "quantity": r.quantity,
            "movement_type": r.movement_type,
            "document_id": doc[0] if doc else None,
            "document_no": doc[1] if doc else None,
            "document_date": doc[2] if doc else None,
            "migrated": r.migrated,
            "created_at": r.created_at,
        })
    return out


@dataclass
class UpstreamSpec:
    """明細が参照する「1つ上位の明細」の定義。

    例: 売上明細 → 受注明細（line_field="order_line_id"）。
    same_partner=True なら、上位伝票と同じ取引先でなければ連携できない
    （受注→発注は得意先と仕入先が別になるため False）。
    """

    line_field: str  # 下位明細側の列名。例: "order_line_id"
    line_model: type
    header_fk: str  # 上位明細から上位ヘッダへの列名。例: "order_id"
    header_model: type
    status_field: str  # 上位ヘッダの状態列
    same_partner: bool = True
    check_product: bool = True  # 入金/支払（金額のみ）以外は商品の一致を確認する


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
    upstream: UpstreamSpec | None = None
    # 在庫を動かす伝票: "purchase"（仕入＝入庫）/ "sales"（売上＝出庫）。それ以外は None
    movement: str | None = None

    def validate_upstream(
        self, db: Session, partner_id: int, lines_data: list[dict[str, Any]], *, check_status: bool = True
    ) -> None:
        """上位明細への連携が正しいかを確認する。

        存在しない明細・取り消し済みの伝票・別の取引先の伝票・別の商品の明細に
        つなぐと残数がおかしくなるため、登録前に止める。
        """
        spec = self.upstream
        if spec is None:
            return
        ids = {line.get(spec.line_field) for line in lines_data} - {None}
        if not ids:
            return
        rows = db.execute(
            select(spec.line_model, spec.header_model)
            .join(spec.header_model, getattr(spec.line_model, spec.header_fk) == spec.header_model.id)
            .where(spec.line_model.id.in_(ids))
        ).all()
        found = {line.id: (line, header) for line, header in rows}
        for i, line in enumerate(lines_data, start=1):
            up_id = line.get(spec.line_field)
            if up_id is None:
                continue
            pair = found.get(up_id)
            if pair is None:
                raise ValueError(f"{i}行目: 連携先の明細（ID {up_id}）が見つかりません")
            up_line, up_header = pair
            status = getattr(up_header, spec.status_field)
            if check_status and getattr(status, "value", status) in ("cancelled", "rejected"):
                raise ValueError(f"{i}行目: 連携先の伝票は取り消し済みです")
            if spec.same_partner and up_header.partner_id != partner_id:
                raise ValueError(f"{i}行目: 連携先の伝票と取引先が違います")
            if spec.check_product and line.get("product_id") is not None and up_line.product_id != line["product_id"]:
                raise ValueError(f"{i}行目: 連携先の明細と商品が違います")

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
        if not lines_data:
            raise ValueError("明細を 1 行以上入力してください")
        self.validate_upstream(db, header_data["partner_id"], lines_data)
        if self.movement:
            lines_data = [fill_warehouse(db, line) for line in lines_data]
        doc_no = self._next_no(db)
        header_kwargs = dict(header_data)
        if hasattr(self.header_model, "created_by"):
            header_kwargs["created_by"] = created_by
        header = self.header_model(**header_kwargs, **{self.no_field: doc_no})  # type: ignore[call-arg]
        db.add(header)
        db.flush()  # header.id を確定させる

        partner = None
        if self.lines_have_qty:
            partner = db.get(models.Partner, header_data["partner_id"])

        for i, line in enumerate(lines_data, start=1):
            if self.lines_have_qty:
                line = resolve_line_amount(line, partner)  # type: ignore[arg-type]
            db.add(self.line_model(**{self.line_fk_name: header.id, "line_no": i}, **line))  # type: ignore[call-arg]
        if self.movement:
            db.flush()
            db.refresh(header)
            sync_inventory_movements(db, self.movement, header, getattr(header, self.lines_relationship))
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
                if self.movement and "warehouse_id" in line_patch:
                    if line_patch["warehouse_id"] is None:
                        line_patch.pop("warehouse_id")  # 空なら今の倉庫のまま
                    elif db.get(models.Warehouse, line_patch["warehouse_id"]) is None:
                        raise ValueError("指定した倉庫が見つかりません")
                for key, value in line_patch.items():
                    if key not in type(line).__table__.columns:  # type: ignore[attr-defined]
                        continue  # この伝票の明細にない項目（例: 見積の倉庫）は無視する
                    setattr(line, key, value)
                if self.lines_have_qty:
                    if line.quantity is not None and line.unit_price is not None:
                        # 数量・単価が両方揃った時点で、明細作成時にスナップショットした
                        # rounding_type（＝その時の取引先マスタの設定）で再計算する。
                        # 取引先マスタの現在の丸め区分は参照しない。
                        line.amount = compute_amount(line.quantity, line.unit_price, line.rounding_type)
                    elif "amount" in line_patch and line_patch["amount"] is not None:
                        line.amount = _to_integer_amount(line_patch["amount"])

        if self.upstream is not None and ("partner_id" in header_data or lines_data):
            # 取引先や商品を変えたことで、上位伝票との連携が食い違わないかを確認する。
            # 上位伝票があとから取り消された場合でも、この伝票の訂正・取消はできるように状態は見ない。
            current = [
                {self.upstream.line_field: getattr(line, self.upstream.line_field), "product_id": getattr(line, "product_id", None)}
                for line in getattr(header, self.lines_relationship)
            ]
            try:
                self.validate_upstream(db, header.partner_id, current, check_status=False)  # type: ignore[attr-defined]
            except ValueError:
                db.rollback()
                raise

        if self.movement:
            # 数量・商品・倉庫の訂正や、取消・下書きへの変更を在庫数に反映する
            db.flush()
            sync_inventory_movements(db, self.movement, header, getattr(header, self.lines_relationship))
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
    upstream=UpstreamSpec("quotation_line_id", models.QuotationLine, "quotation_id", models.Quotation, "approval_status"),
)
purchase_order_crud: DocumentCRUD[models.PurchaseOrder, models.PurchaseOrderLine] = DocumentCRUD(
    models.PurchaseOrder, models.PurchaseOrderLine, "purchase_order_id", "purchase_order_no", "PO", "lines",
    date_field="order_date", status_field="status",
    # 受注（得意先）→ 発注（仕入先）なので取引先は一致しない
    upstream=UpstreamSpec("order_line_id", models.OrderLine, "order_id", models.Order, "status", same_partner=False),
)
purchase_crud: DocumentCRUD[models.Purchase, models.PurchaseLine] = DocumentCRUD(
    models.Purchase, models.PurchaseLine, "purchase_id", "purchase_no", "PU", "lines",
    date_field="purchase_date", status_field="status", movement="purchase",
    upstream=UpstreamSpec("purchase_order_line_id", models.PurchaseOrderLine, "purchase_order_id", models.PurchaseOrder, "status"),
)
sales_crud: DocumentCRUD[models.Sales, models.SalesLine] = DocumentCRUD(
    models.Sales, models.SalesLine, "sales_id", "sales_no", "SA", "lines",
    date_field="sales_date", status_field="status", movement="sales",
    upstream=UpstreamSpec("order_line_id", models.OrderLine, "order_id", models.Order, "status"),
)
receipt_crud: DocumentCRUD[models.Receipt, models.ReceiptLine] = DocumentCRUD(
    models.Receipt, models.ReceiptLine, "receipt_id", "receipt_no", "RC", "lines",
    date_field="receipt_date", status_field="status", lines_have_qty=False,
    upstream=UpstreamSpec("sales_line_id", models.SalesLine, "sales_id", models.Sales, "status", check_product=False),
)
payment_crud: DocumentCRUD[models.Payment, models.PaymentLine] = DocumentCRUD(
    models.Payment, models.PaymentLine, "payment_id", "payment_no", "PM", "lines",
    date_field="payment_date", status_field="status", lines_have_qty=False,
    upstream=UpstreamSpec("purchase_line_id", models.PurchaseLine, "purchase_id", models.Purchase, "status", check_product=False),
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


# ------------------------------------------------------------
# 残のある上位明細（下位伝票の「上位伝票から取り込む」用）
# ------------------------------------------------------------
@dataclass
class OpenLineSource:
    line_model: type
    header_fk: str
    header_model: type
    no_field: str
    date_field: str
    status_field: str
    view_model: type
    view_line_field: str
    remaining_field: str
    is_amount: bool = False


OPEN_LINE_SOURCES: dict[str, OpenLineSource] = {
    # 受注の作成で使う: 見積の残
    "quotation": OpenLineSource(
        models.QuotationLine, "quotation_id", models.Quotation, "quotation_no", "quotation_date", "approval_status",
        models.QuotationRemaining, "quotation_line_id", "remaining_qty",
    ),
    # 発注の作成で使う: 受注のうち、まだ発注していない数量
    "order_for_purchase": OpenLineSource(
        models.OrderLine, "order_id", models.Order, "order_no", "order_date", "status",
        models.OrderRemainingForPurchase, "order_line_id", "remaining_qty",
    ),
    # 売上の作成で使う: 受注のうち、まだ売上にしていない数量
    "order_for_sales": OpenLineSource(
        models.OrderLine, "order_id", models.Order, "order_no", "order_date", "status",
        models.OrderRemainingForSales, "order_line_id", "remaining_qty",
    ),
    # 仕入の作成で使う: 発注残
    "purchase_order": OpenLineSource(
        models.PurchaseOrderLine, "purchase_order_id", models.PurchaseOrder, "purchase_order_no", "order_date", "status",
        models.PurchaseOrderRemaining, "purchase_order_line_id", "remaining_qty",
    ),
    # 入金の作成で使う: 未入金
    "sales": OpenLineSource(
        models.SalesLine, "sales_id", models.Sales, "sales_no", "sales_date", "status",
        models.SalesRemainingForReceipt, "sales_line_id", "remaining_amount", is_amount=True,
    ),
    # 支払の作成で使う: 未払
    "purchase": OpenLineSource(
        models.PurchaseLine, "purchase_id", models.Purchase, "purchase_no", "purchase_date", "status",
        models.PurchaseRemainingForPayment, "purchase_line_id", "remaining_amount", is_amount=True,
    ),
}


def list_open_lines(db: Session, kind: str, *, partner_id: int | None = None, limit: int = 200) -> list[dict]:
    """残（数量または金額）が残っている上位明細を、古い伝票から順に返す。"""
    src = OPEN_LINE_SOURCES[kind]
    line_m, header_m, view_m = src.line_model, src.header_model, src.view_model
    status_col = getattr(header_m, src.status_field)
    remaining_col = getattr(view_m, src.remaining_field)
    stmt = (
        select(line_m, header_m, remaining_col)
        .join(header_m, getattr(line_m, src.header_fk) == header_m.id)
        .join(view_m, getattr(view_m, src.view_line_field) == line_m.id)
        .where(status_col != ("rejected" if src.status_field == "approval_status" else "cancelled"))
        .where(remaining_col > 0)
    )
    if partner_id is not None:
        stmt = stmt.where(header_m.partner_id == partner_id)
    stmt = stmt.order_by(getattr(header_m, src.date_field), header_m.id, line_m.line_no).limit(limit)
    rows = db.execute(stmt).all()

    attach_partner_names(db, [r[1] for r in rows])
    attach_product_names(db, [r[0] for r in rows])
    return [
        {
            "line_id": line.id,
            "document_id": header.id,
            "document_no": getattr(header, src.no_field),
            "document_date": getattr(header, src.date_field),
            "partner_id": header.partner_id,
            "partner_name": header.partner_name,  # type: ignore[attr-defined]
            "line_no": line.line_no,
            "product_id": line.product_id,
            "product_code": line.product_code,  # type: ignore[attr-defined]
            "product_name": line.product_name,  # type: ignore[attr-defined]
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "amount": line.amount,
            "remaining_qty": None if src.is_amount else remaining,
            "remaining_amount": remaining if src.is_amount else None,
        }
        for line, header, remaining in rows
    ]


# ------------------------------------------------------------
# 使える在庫の見込み（在庫 − 引当 + 入荷予定）
# ------------------------------------------------------------
def _sum_allocations_by_line(db: Session, stage: models.AllocationStage, line_attr: str) -> dict[int, tuple[int, Decimal]]:
    out: dict[int, tuple[int, Decimal]] = {}
    for a in db.execute(
        select(models.InventoryAllocation).where(models.InventoryAllocation.allocation_stage == stage)
    ).scalars():
        line_id = getattr(a, line_attr)
        pid, total = out.get(line_id, (a.product_id, Decimal(0)))
        out[line_id] = (pid, total + Decimal(a.quantity))
    return out


def inventory_availability(db: Session, *, keyword: str | None = None) -> list[dict]:
    """商品ごとに「いまある在庫・引当中・入荷予定・使える見込み」を計算する。

    引当は時点ごとに別々に持つが、二重に数えないように次の考え方で数える。
    - 見積時点の引当: その見積明細にまだ残（受注していない数量）がある分だけ数える。
      受注に進んだ分は、受注時点の引当に役目を引き継いだものとして外す。
    - 受注時点の引当: その受注明細にまだ売上にしていない数量がある分だけ数える。
    - 売上時点の引当: 売上が下書きの間だけ数える。売上を確定すると在庫数そのものが減る
      （在庫の受払）ため、引当としては外す。
    - 入荷予定: 取り消されていない発注の発注残。
    """
    on_hand: dict[int, Decimal] = defaultdict(Decimal)
    for product_id, qty in db.execute(
        select(models.InventoryStock.product_id, models.InventoryStock.quantity_on_hand)
    ).all():
        on_hand[product_id] += Decimal(qty or 0)

    allocated: dict[int, Decimal] = defaultdict(Decimal)

    q_alloc = _sum_allocations_by_line(db, models.AllocationStage.quotation, "quotation_line_id")
    if q_alloc:
        rem = {
            r.quotation_line_id: Decimal(r.remaining_qty or 0)
            for r in db.execute(
                select(models.QuotationRemaining)
                .join(models.Quotation, models.Quotation.id == models.QuotationRemaining.quotation_id)
                .where(models.QuotationRemaining.quotation_line_id.in_(q_alloc.keys()))
                .where(models.Quotation.approval_status != models.ApprovalStatus.rejected)
            ).scalars()
        }
        for line_id, (pid, total) in q_alloc.items():
            allocated[pid] += min(total, rem.get(line_id, Decimal(0)))

    o_alloc = _sum_allocations_by_line(db, models.AllocationStage.order, "order_line_id")
    if o_alloc:
        rem = {
            r.order_line_id: Decimal(r.remaining_qty or 0)
            for r in db.execute(
                select(models.OrderRemainingForSales)
                .join(models.Order, models.Order.id == models.OrderRemainingForSales.order_id)
                .where(models.OrderRemainingForSales.order_line_id.in_(o_alloc.keys()))
                .where(models.Order.status != models.DocumentStatus.cancelled)
            ).scalars()
        }
        for line_id, (pid, total) in o_alloc.items():
            allocated[pid] += min(total, rem.get(line_id, Decimal(0)))

    for pid, qty in db.execute(
        select(models.InventoryAllocation.product_id, models.InventoryAllocation.quantity)
        .join(models.SalesLine, models.SalesLine.id == models.InventoryAllocation.sales_line_id)
        .join(models.Sales, models.Sales.id == models.SalesLine.sales_id)
        .where(models.InventoryAllocation.allocation_stage == models.AllocationStage.sales)
        .where(models.Sales.status == models.DocumentStatus.draft)
    ).all():
        allocated[pid] += Decimal(qty)

    incoming: dict[int, Decimal] = defaultdict(Decimal)
    for pid, qty in db.execute(
        select(models.PurchaseOrderLine.product_id, models.PurchaseOrderRemaining.remaining_qty)
        .join(models.PurchaseOrderRemaining, models.PurchaseOrderRemaining.purchase_order_line_id == models.PurchaseOrderLine.id)
        .join(models.PurchaseOrder, models.PurchaseOrder.id == models.PurchaseOrderLine.purchase_order_id)
        .where(models.PurchaseOrder.status != models.DocumentStatus.cancelled)
    ).all():
        incoming[pid] += Decimal(qty or 0)

    product_ids = set(on_hand) | {p for p, v in allocated.items() if v} | {p for p, v in incoming.items() if v}
    if not product_ids:
        return []
    stmt = select(models.Product).where(models.Product.id.in_(product_ids))
    if keyword:
        stmt = stmt.where((models.Product.product_code.ilike(f"%{keyword}%")) | (models.Product.name.ilike(f"%{keyword}%")))
    products = db.execute(stmt.order_by(models.Product.product_code)).scalars().all()
    return [
        {
            "product_id": p.id,
            "product_code": p.product_code,
            "product_name": p.name,
            "unit": p.unit,
            "on_hand": on_hand[p.id],
            "allocated": allocated[p.id],
            "incoming": incoming[p.id],
            "available": on_hand[p.id] - allocated[p.id] + incoming[p.id],
        }
        for p in products
    ]
