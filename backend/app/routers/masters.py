from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..security import SessionUser, get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


# ------------------------------------------------------------
# 取引先（共通マスタ / 顧客管理）
# ------------------------------------------------------------
@router.get("/partners", response_model=list[schemas.PartnerWithCurrentDetailOut], tags=["共通マスタ", "顧客管理"])
def list_partners(
    partner_type: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    partners = crud.list_partners(db, partner_type=partner_type, keyword=keyword, limit=page_size, offset=(page - 1) * page_size)
    return [_partner_with_current(p) for p in partners]


@router.post("/partners", response_model=schemas.PartnerOut, status_code=201, tags=["共通マスタ"])
def create_partner(payload: schemas.PartnerCreateRequest, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.create_partner(
        db,
        partner_code=payload.partner_code,
        partner_type=payload.partner_type.value,
        detail=payload.detail.model_dump(),
        created_by=user.id,
    )


@router.get("/partners/{partner_id}", response_model=schemas.PartnerWithCurrentDetailOut, tags=["共通マスタ", "顧客管理"])
def get_partner(partner_id: int, as_of: date | None = None, db: Session = Depends(get_db)):
    partner = crud.get_partner(db, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="partner not found")
    return _partner_with_current(partner, as_of=as_of)


@router.patch("/partners/{partner_id}", response_model=schemas.PartnerOut, tags=["共通マスタ"])
def patch_partner(partner_id: int, payload: schemas.PartnerPatchRequest, db: Session = Depends(get_db)):
    partner = crud.get_partner(db, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="partner not found")
    partner_type = payload.partner_type.value if payload.partner_type else None
    return crud.update_partner_flags(db, partner, partner_type=partner_type, is_active=payload.is_active)


@router.get("/partners/{partner_id}/details", response_model=list[schemas.PartnerDetailOut], tags=["顧客管理"])
def list_partner_details(partner_id: int, db: Session = Depends(get_db)):
    return crud.list_partner_details(db, partner_id)


@router.post("/partners/{partner_id}/details", response_model=schemas.PartnerDetailOut, status_code=201, tags=["顧客管理"])
def add_partner_detail(
    partner_id: int, payload: schemas.PartnerDetailIn, user: SessionUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    if crud.get_partner(db, partner_id) is None:
        raise HTTPException(status_code=404, detail="partner not found")
    return crud.add_partner_detail(db, partner_id, payload.model_dump(), created_by=user.id)


@router.get("/partners/{partner_id}/transactions", response_model=schemas.TransactionHistoryResponse, tags=["顧客管理"])
def partner_transactions(
    partner_id: int,
    type: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if crud.get_partner(db, partner_id) is None:
        raise HTTPException(status_code=404, detail="partner not found")
    items = crud.partner_transactions(db, partner_id, types=type)
    return schemas.TransactionHistoryResponse(
        data=[schemas.TransactionHistoryItem.model_validate(i) for i in items],
        meta=schemas.PageMeta(page=1, page_size=len(items), total_count=len(items)),
    )


def _partner_with_current(partner, as_of: date | None = None) -> schemas.PartnerWithCurrentDetailOut:
    if as_of is None:
        current = partner.current_detail
    else:
        candidates = [d for d in partner.details if d.effective_date <= as_of]
        current = max(candidates, key=lambda d: (d.effective_date, d.id)) if candidates else None
    data = schemas.PartnerOut.model_validate(partner).model_dump(by_alias=True)
    data["currentDetail"] = schemas.PartnerDetailOut.model_validate(current).model_dump(by_alias=True) if current else None
    return schemas.PartnerWithCurrentDetailOut.model_validate(data)


# ------------------------------------------------------------
# 商品
# ------------------------------------------------------------
@router.get("/products", response_model=list[schemas.ProductOut], tags=["共通マスタ"])
def list_products(
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return crud.list_products(db, keyword=keyword, limit=page_size, offset=(page - 1) * page_size)


@router.post("/products", response_model=schemas.ProductOut, status_code=201, tags=["共通マスタ"])
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db)):
    return crud.create_product(db, payload.model_dump())


@router.get("/products/{product_id}", response_model=schemas.ProductOut, tags=["共通マスタ"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.patch("/products/{product_id}", response_model=schemas.ProductOut, tags=["共通マスタ"])
def update_product(product_id: int, payload: schemas.ProductIn, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return crud.update_product(db, product, payload.model_dump())


# ------------------------------------------------------------
# 単価
# ------------------------------------------------------------
@router.get("/price-master", response_model=list[schemas.PriceMasterOut], tags=["共通マスタ"])
def list_price_master(
    price_type: str | None = None,
    partner_id: int | None = None,
    product_id: int | None = None,
    as_of: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_price_master(
        db,
        price_type=price_type,
        partner_id=partner_id,
        product_id=product_id,
        as_of=as_of,
        limit=page_size,
        offset=(page - 1) * page_size,
    )


@router.post("/price-master", response_model=schemas.PriceMasterOut, status_code=201, tags=["共通マスタ"])
def create_price_master(payload: schemas.PriceMasterIn, db: Session = Depends(get_db)):
    return crud.create_price_master(db, payload.model_dump())


@router.get("/price-master/{price_id}", response_model=schemas.PriceMasterOut, tags=["共通マスタ"])
def get_price_master(price_id: int, db: Session = Depends(get_db)):
    row = crud.get_price_master(db, price_id)
    if row is None:
        raise HTTPException(status_code=404, detail="price not found")
    return row


@router.patch("/price-master/{price_id}", response_model=schemas.PriceMasterOut, tags=["共通マスタ"])
def update_price_master(price_id: int, payload: schemas.PriceMasterPatch, db: Session = Depends(get_db)):
    row = db.get(models.PriceMaster, price_id)
    if row is None:
        raise HTTPException(status_code=404, detail="price not found")
    return crud.update_price_master(db, row, payload.model_dump(exclude_unset=True))


# ------------------------------------------------------------
# 倉庫
# ------------------------------------------------------------
@router.get("/warehouses", response_model=list[schemas.WarehouseOut], tags=["共通マスタ"])
def list_warehouses(db: Session = Depends(get_db)):
    return crud.list_warehouses(db)
