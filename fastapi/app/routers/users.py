from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import DbSessionDep
from ..models import User as UserModel
from ..schemas.users import UserCreate, UserRead, UserUpdate
from ..utils.db import apply_updates, validate_uniqueness

router = APIRouter()


@router.get("/", response_model=List[UserRead])
def list_users(db: DbSessionDep):
    return db.query(UserModel).order_by(UserModel.id).all()


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj


@router.post("/", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: DbSessionDep):
    # Basic uniqueness check (DB also enforces)
    validate_uniqueness(db, UserModel, [UserModel.username == payload.username], error_message="Username already exists")
    validate_uniqueness(db, UserModel, [UserModel.email == payload.email], error_message="Email already exists")

    obj = UserModel(username=payload.username, email=payload.email)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)

    if "username" in data and data["username"] != obj.username:
        validate_uniqueness(db, UserModel, [UserModel.username == data["username"]], exclude_id=obj.id, error_message="Username already exists")
    if "email" in data and data["email"] != obj.email:
        validate_uniqueness(db, UserModel, [UserModel.email == data["email"]], exclude_id=obj.id, error_message="Email already exists")

    apply_updates(obj, data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSessionDep):
    obj = db.get(UserModel, user_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return None
