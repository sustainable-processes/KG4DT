from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import DbSessionDep
from ..models import User as UserModel
from ..schemas.users import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["v1: users"])
# Non-versioned duplicate under /api/users
router_nv = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserRead])
def list_users(db: DbSessionDep):
    return db.query(UserModel).order_by(UserModel.id).all()


@router_nv.get("/", response_model=List[UserRead])
def list_users_nv(db: DbSessionDep):
    return list_users(db)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj


@router_nv.get("/{user_id}", response_model=UserRead)
def get_user_nv(user_id: int, db: DbSessionDep):
    return get_user(user_id, db)


@router.post("/", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: DbSessionDep):
    # Basic uniqueness check (DB also enforces)
    exists = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=409, detail="Username already exists")
    exists = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")
    obj = UserModel(username=payload.username, email=payload.email)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.post("/", response_model=UserRead, status_code=201)
def create_user_nv(payload: UserCreate, db: DbSessionDep):
    return create_user(payload, db)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "username" in data and data["username"] != obj.username:
        exists = db.query(UserModel).filter(UserModel.username == data["username"]).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")
    if "email" in data and data["email"] != obj.email:
        exists = db.query(UserModel).filter(UserModel.email == data["email"]).first()
        if exists:
            raise HTTPException(status_code=409, detail="Email already exists")
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router_nv.patch("/{user_id}", response_model=UserRead)
def update_user_nv(user_id: int, payload: UserUpdate, db: DbSessionDep):
    return update_user(user_id, payload, db)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return None


@router_nv.delete("/{user_id}", status_code=204)
def delete_user_nv(user_id: int, db: DbSessionDep):
    return delete_user(user_id, db)
