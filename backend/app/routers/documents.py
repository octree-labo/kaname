"""見積〜支払の伝票チェーン。

各伝票はヘッダ＋明細＋（任意の）上位明細への連携という共通構造を持つため、
crud.DocumentCRUD を通じて list/create/get/update の基本操作を共通化している。
残数を含む明細一覧や、見積特有の承認/PDF/受注確定は個別に実装する。

PATCH は既存明細の product/quantity/unitPrice（または amount）のみ変更できる。
明細の追加・削除はサポートしない（下位伝票から参照された明細を削除すると
外部キー制約違反になるため、安全側に倒して「既存行の更新」のみに限定している）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..pdf import render_quotation_pdf
from ..security import SessionUser, get_current_user, get_viewer

router = APIRouter(dependencies=[Depends(get_viewer)])


def _lines(lines: list[Any]) -> list[dict]:
    return [line.model_dump() for line in lines]


def _patch_lines(lines: list[Any] | None) -> list[dict] | None:
    if lines is None:
        return None
    return [line.model_dump(exclude_unset=True) for line in lines]


# ============================================================
# 見積
# ============================================================
@router.get("/quotations", response_model=list[schemas.QuotationOut], tags=["見積"])
def list_quotations(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    approval_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.quotation_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=approval_status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/quotations", response_model=schemas.QuotationOut, status_code=201, tags=["見積"])
def create_quotation(payload: schemas.QuotationIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    try:
        return crud.quotation_crud.create(db, header, _lines(payload.lines), created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/quotations/{quotation_id}", response_model=schemas.QuotationDetailOut, tags=["見積"])
def get_quotation(quotation_id: int, db: Session = Depends(get_db)):
    obj = crud.quotation_crud.get(db, quotation_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="quotation not found")
    return obj


@router.patch("/quotations/{quotation_id}", response_model=schemas.QuotationDetailOut, tags=["見積"], dependencies=[Depends(get_current_user)])
def update_quotation(quotation_id: int, payload: schemas.QuotationPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.quotation_crud.update(db, quotation_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="quotation not found")
    return obj


@router.get("/quotations/{quotation_id}/lines", response_model=list[schemas.QuotationLineWithRemainingOut], tags=["見積"])
def get_quotation_lines(quotation_id: int, db: Session = Depends(get_db)):
    if crud.quotation_crud.get(db, quotation_id) is None:
        raise HTTPException(status_code=404, detail="quotation not found")
    return crud.quotation_lines_with_remaining(db, quotation_id)


@router.post("/quotations/{quotation_id}/approve", response_model=schemas.QuotationOut, tags=["見積"])
def approve_quotation(quotation_id: int, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    quotation = db.get(models.Quotation, quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="quotation not found")
    if quotation.approval_status == models.ApprovalStatus.approved:
        raise HTTPException(status_code=409, detail="already approved")
    quotation.approval_status = models.ApprovalStatus.approved
    quotation.approved_by = user.id
    quotation.approved_at = datetime.now(timezone.utc)
    db.commit()
    return crud.quotation_crud.get(db, quotation_id)


@router.get("/quotations/{quotation_id}/pdf", tags=["見積"])
def get_quotation_pdf(quotation_id: int, db: Session = Depends(get_db)):
    quotation = crud.quotation_crud.get(db, quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="quotation not found")
    partner = db.get(models.Partner, quotation.partner_id)
    pdf_bytes = render_quotation_pdf(quotation, partner)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/quotations/{quotation_id}/confirm-orders", response_model=schemas.OrderOut, status_code=201, tags=["見積", "受注"])
def confirm_orders(
    quotation_id: int,
    payload: schemas.QuotationConfirmOrdersRequest,
    user: SessionUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quotation = crud.quotation_crud.get(db, quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="quotation not found")

    if payload.mode == "whole_document":
        selections = [(line.id, line.quantity) for line in quotation.lines]
    elif payload.mode == "selected_lines":
        selections = [(s.quotation_line_id, s.quantity) for s in payload.line_selections]
    else:
        raise HTTPException(status_code=400, detail="mode must be whole_document or selected_lines")

    lines_data = []
    quotation_line_by_id = {line.id: line for line in quotation.lines}
    for line_id, qty in selections:
        q_line = quotation_line_by_id.get(line_id)
        if q_line is None:
            raise HTTPException(status_code=400, detail=f"invalid quotation line: {line_id}")
        quantity = qty if qty is not None else q_line.quantity
        line_data: dict[str, Any] = {"quotation_line_id": q_line.id, "product_id": q_line.product_id}
        if quantity is not None and q_line.unit_price is not None:
            # 数量・単価が両方揃っている場合は受注側で（受注の取引先の丸め区分で）再計算させる
            line_data["quantity"] = quantity
            line_data["unit_price"] = q_line.unit_price
        else:
            # 見積側が金額のみ手入力だった場合は、その金額をそのまま引き継ぐ
            line_data["amount"] = q_line.amount
        lines_data.append(line_data)

    header = {"partner_id": quotation.partner_id, "order_date": date.today()}
    try:
        return crud.order_crud.create(db, header, lines_data, created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 受注
# ============================================================
@router.get("/orders", response_model=list[schemas.OrderOut], tags=["受注"])
def list_orders(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.order_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/orders", response_model=schemas.OrderOut, status_code=201, tags=["受注"])
def create_order(payload: schemas.OrderIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    try:
        return crud.order_crud.create(db, header, _lines(payload.lines), created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}", response_model=schemas.OrderDetailOut, tags=["受注"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    obj = crud.order_crud.get(db, order_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="order not found")
    return obj


@router.patch("/orders/{order_id}", response_model=schemas.OrderDetailOut, tags=["受注"], dependencies=[Depends(get_current_user)])
def update_order(order_id: int, payload: schemas.OrderPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.order_crud.update(db, order_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="order not found")
    return obj


@router.get("/orders/{order_id}/lines", response_model=list[schemas.OrderLineWithRemainingOut], tags=["受注"])
def get_order_lines(order_id: int, db: Session = Depends(get_db)):
    if crud.order_crud.get(db, order_id) is None:
        raise HTTPException(status_code=404, detail="order not found")
    return crud.order_lines_with_remaining(db, order_id)


# ============================================================
# 発注
# ============================================================
@router.get("/purchase-orders", response_model=list[schemas.PurchaseOrderOut], tags=["発注"])
def list_purchase_orders(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.purchase_order_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/purchase-orders", response_model=schemas.PurchaseOrderOut, status_code=201, tags=["発注"])
def create_purchase_order(payload: schemas.PurchaseOrderIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    try:
        return crud.purchase_order_crud.create(db, header, _lines(payload.lines), created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchase-orders/{purchase_order_id}", response_model=schemas.PurchaseOrderDetailOut, tags=["発注"])
def get_purchase_order(purchase_order_id: int, db: Session = Depends(get_db)):
    obj = crud.purchase_order_crud.get(db, purchase_order_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return obj


@router.patch("/purchase-orders/{purchase_order_id}", response_model=schemas.PurchaseOrderDetailOut, tags=["発注"], dependencies=[Depends(get_current_user)])
def update_purchase_order(purchase_order_id: int, payload: schemas.PurchaseOrderPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.purchase_order_crud.update(db, purchase_order_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return obj


@router.get(
    "/purchase-orders/{purchase_order_id}/lines",
    response_model=list[schemas.PurchaseOrderLineWithRemainingOut],
    tags=["発注"],
)
def get_purchase_order_lines(purchase_order_id: int, db: Session = Depends(get_db)):
    if crud.purchase_order_crud.get(db, purchase_order_id) is None:
        raise HTTPException(status_code=404, detail="purchase order not found")
    return crud.purchase_order_lines_with_remaining(db, purchase_order_id)


# ============================================================
# 仕入
# ============================================================
@router.get("/purchases", response_model=list[schemas.PurchaseOut], tags=["仕入"])
def list_purchases(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.purchase_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/purchases", response_model=schemas.PurchaseOut, status_code=201, tags=["仕入"])
def create_purchase(payload: schemas.PurchaseIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    try:
        return crud.purchase_crud.create(db, header, _lines(payload.lines), created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchases/{purchase_id}", response_model=schemas.PurchaseDetailOut, tags=["仕入"])
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    obj = crud.purchase_crud.get(db, purchase_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="purchase not found")
    return obj


@router.patch("/purchases/{purchase_id}", response_model=schemas.PurchaseDetailOut, tags=["仕入"], dependencies=[Depends(get_current_user)])
def update_purchase(purchase_id: int, payload: schemas.PurchasePatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.purchase_crud.update(db, purchase_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="purchase not found")
    return obj


# ============================================================
# 売上
# ============================================================
@router.get("/sales", response_model=list[schemas.SalesOut], tags=["売上"])
def list_sales(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.sales_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/sales", response_model=schemas.SalesOut, status_code=201, tags=["売上"])
def create_sales(payload: schemas.SalesIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    try:
        return crud.sales_crud.create(db, header, _lines(payload.lines), created_by=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sales/{sales_id}", response_model=schemas.SalesDetailOut, tags=["売上"])
def get_sales(sales_id: int, db: Session = Depends(get_db)):
    obj = crud.sales_crud.get(db, sales_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="sales not found")
    return obj


@router.patch("/sales/{sales_id}", response_model=schemas.SalesDetailOut, tags=["売上"], dependencies=[Depends(get_current_user)])
def update_sales(sales_id: int, payload: schemas.SalesPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.sales_crud.update(db, sales_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="sales not found")
    return obj


# ============================================================
# 入金
# ============================================================
@router.get("/receipts", response_model=list[schemas.ReceiptOut], tags=["入金"])
def list_receipts(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.receipt_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/receipts", response_model=schemas.ReceiptOut, status_code=201, tags=["入金"])
def create_receipt(payload: schemas.ReceiptIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    lines_data = [line.model_dump() for line in payload.lines]
    return crud.receipt_crud.create(db, header, lines_data, created_by=user.id)


@router.get("/receipts/{receipt_id}", response_model=schemas.ReceiptDetailOut, tags=["入金"])
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    obj = crud.receipt_crud.get(db, receipt_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    return obj


@router.patch("/receipts/{receipt_id}", response_model=schemas.ReceiptDetailOut, tags=["入金"], dependencies=[Depends(get_current_user)])
def update_receipt(receipt_id: int, payload: schemas.ReceiptPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.receipt_crud.update(db, receipt_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    return obj


# ============================================================
# 支払
# ============================================================
@router.get("/payments", response_model=list[schemas.PaymentOut], tags=["支払"])
def list_payments(
    partner_id: int | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.payment_crud.list(
        db, partner_id=partner_id, keyword=keyword, date_from=date_from, date_to=date_to,
        status=status, limit=page_size, offset=(page - 1) * page_size,
    )


@router.post("/payments", response_model=schemas.PaymentOut, status_code=201, tags=["支払"])
def create_payment(payload: schemas.PaymentIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    header = payload.model_dump(exclude={"lines"})
    lines_data = [line.model_dump() for line in payload.lines]
    return crud.payment_crud.create(db, header, lines_data, created_by=user.id)


@router.get("/payments/{payment_id}", response_model=schemas.PaymentDetailOut, tags=["支払"])
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    obj = crud.payment_crud.get(db, payment_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return obj


@router.patch("/payments/{payment_id}", response_model=schemas.PaymentDetailOut, tags=["支払"], dependencies=[Depends(get_current_user)])
def update_payment(payment_id: int, payload: schemas.PaymentPatch, db: Session = Depends(get_db)):
    header_data = payload.model_dump(exclude_unset=True, exclude={"lines"})
    try:
        obj = crud.payment_crud.update(db, payment_id, header_data, _patch_lines(payload.lines))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if obj is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return obj
