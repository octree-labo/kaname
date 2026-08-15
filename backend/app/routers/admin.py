"""オーナーメニュー: アカウント申請の一覧・承認・却下。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_owner

router = APIRouter(prefix="/admin", tags=["オーナーメニュー"], dependencies=[Depends(get_current_owner)])


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(models.User).order_by(models.User.created_at.desc())
    if status is not None:
        stmt = stmt.where(models.User.status == status)
    return list(db.execute(stmt).scalars().all())


@router.post("/users/{user_id}/approve", response_model=schemas.AdminUserOut)
def approve_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if user.role == models.UserRole.owner:
        raise HTTPException(status_code=400, detail="owner account cannot be modified here")
    user.status = models.UserStatus.approved
    user.role = models.UserRole.member
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reject", response_model=schemas.AdminUserOut)
def reject_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if user.role == models.UserRole.owner:
        raise HTTPException(status_code=400, detail="owner account cannot be modified here")
    user.status = models.UserStatus.rejected
    db.commit()
    db.refresh(user)
    return user
