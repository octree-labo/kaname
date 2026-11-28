from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..security import get_current_user, get_viewer

router = APIRouter(prefix="/inventory", tags=["在庫"], dependencies=[Depends(get_viewer)])


@router.get("/stocks", response_model=list[schemas.InventoryStockOut])
def list_stocks(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(models.InventoryStock)
    if product_id is not None:
        stmt = stmt.where(models.InventoryStock.product_id == product_id)
    if warehouse_id is not None:
        stmt = stmt.where(models.InventoryStock.warehouse_id == warehouse_id)
    if keyword:
        stmt = stmt.join(models.Product, models.Product.id == models.InventoryStock.product_id).where(
            (models.Product.product_code.ilike(f"%{keyword}%")) | (models.Product.name.ilike(f"%{keyword}%"))
        )
    rows = list(db.execute(stmt).scalars().all())
    crud.attach_product_names(db, rows)
    crud.attach_warehouse_names(db, rows)
    return rows


@router.get("/allocations", response_model=list[schemas.InventoryAllocationOut])
def list_allocations(
    product_id: int | None = None,
    stage: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(models.InventoryAllocation)
    if product_id is not None:
        stmt = stmt.where(models.InventoryAllocation.product_id == product_id)
    if stage is not None:
        stmt = stmt.where(models.InventoryAllocation.allocation_stage == stage)
    if keyword:
        stmt = stmt.join(models.Product, models.Product.id == models.InventoryAllocation.product_id).where(
            (models.Product.product_code.ilike(f"%{keyword}%")) | (models.Product.name.ilike(f"%{keyword}%"))
        )
    rows = list(db.execute(stmt).scalars().all())
    crud.attach_product_names(db, rows)
    crud.attach_warehouse_names(db, rows)
    return rows


@router.get("/availability", response_model=list[schemas.InventoryAvailabilityOut])
def list_availability(keyword: str | None = None, db: Session = Depends(get_db)):
    """商品ごとの「在庫 − 引当 + 入荷予定 = 使える見込み」。"""
    return crud.inventory_availability(db, keyword=keyword)


_STAGE_LINE = {
    "quotation": ("quotation_line_id", models.QuotationLine),
    "order": ("order_line_id", models.OrderLine),
    "sales": ("sales_line_id", models.SalesLine),
}


@router.post("/allocations", response_model=schemas.InventoryAllocationOut, status_code=201, dependencies=[Depends(get_current_user)])
def create_allocation(payload: schemas.InventoryAllocationIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    stage = data["allocation_stage"]
    if stage not in _STAGE_LINE:
        raise HTTPException(status_code=400, detail="引当段階は quotation / order / sales のどれかを指定してください")
    field, line_model = _STAGE_LINE[stage]
    for other, _ in _STAGE_LINE.values():
        if other != field:
            data[other] = None  # 段階と違う明細IDは使わない（DBのCHECK制約違反を防ぐ）
    if data[field] is None:
        raise HTTPException(status_code=400, detail="引当する明細を指定してください")
    line = db.get(line_model, data[field])
    if line is None:
        raise HTTPException(status_code=400, detail="指定した明細が見つかりません")
    if line.product_id != data["product_id"]:
        raise HTTPException(status_code=400, detail="明細の商品と引当の商品が違います")
    if data["quantity"] is None or data["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="引当数量は 0 より大きくしてください")
    row = models.InventoryAllocation(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    crud.attach_product_names(db, [row])
    crud.attach_warehouse_names(db, [row])
    return row
