from __future__ import annotations

from fastapi import APIRouter, Depends
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


@router.post("/allocations", response_model=schemas.InventoryAllocationOut, status_code=201, dependencies=[Depends(get_current_user)])
def create_allocation(payload: schemas.InventoryAllocationIn, db: Session = Depends(get_db)):
    row = models.InventoryAllocation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    crud.attach_product_names(db, [row])
    crud.attach_warehouse_names(db, [row])
    return row
