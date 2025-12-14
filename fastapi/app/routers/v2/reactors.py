from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_

from ...dependencies import DbSessionDep
from ...models.v2 import models as m
from ...schemas.v2.reactors import ReactorCreate, ReactorRead, ReactorUpdate
from ...schemas.v2.basics import BasicRead

router = APIRouter(prefix="/api/v2/reactors", tags=["v2: reactors"])


def _get_reactor_or_404(db: DbSessionDep, reactor_id: int) -> m.Reactor:
    obj = db.get(m.Reactor, reactor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")
    return obj


@router.get("/", response_model=List[ReactorRead])
def list_reactors(
    db: DbSessionDep,
    limit: int = Query(100, ge=0, le=500),
    offset: int = Query(0, ge=0),
):
    q = db.query(m.Reactor).order_by(m.Reactor.updated_at.desc(), m.Reactor.id.desc())
    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{reactor_id}", response_model=ReactorRead)
def get_reactor(reactor_id: int, db: DbSessionDep):
    return _get_reactor_or_404(db, reactor_id)


@router.post("/", response_model=ReactorRead, status_code=201)
def create_reactor(payload: ReactorCreate, db: DbSessionDep):
    obj = m.Reactor(
        name=payload.name,
        number_of_input=payload.number_of_input or 0,
        number_of_output=payload.number_of_output or 0,
        icon_url=payload.icon_url,
        json_data=payload.json_data or {},
        chemistry=payload.chemistry,
        kinetics=payload.kinetics,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{reactor_id}", response_model=ReactorRead)
def update_reactor(reactor_id: int, payload: ReactorUpdate, db: DbSessionDep):
    obj = _get_reactor_or_404(db, reactor_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{reactor_id}", status_code=204)
def delete_reactor(reactor_id: int, db: DbSessionDep):
    obj = _get_reactor_or_404(db, reactor_id)
    db.delete(obj)
    db.commit()
    return None


# Junction management: reactors ↔ basics

@router.get("/{reactor_id}/basics", response_model=List[BasicRead])
def list_reactor_basics(reactor_id: int, db: DbSessionDep):
    _ = _get_reactor_or_404(db, reactor_id)
    basics = (
        db.query(m.Basic)
        .join(m.ReactorBasicJunction, m.ReactorBasicJunction.basic_id == m.Basic.id)
        .filter(m.ReactorBasicJunction.reactor_id == reactor_id)
        .order_by(m.Basic.name.asc())
        .all()
    )
    return basics


@router.post("/{reactor_id}/basics/{basic_id}", status_code=204)
def link_basic(reactor_id: int, basic_id: int, db: DbSessionDep):
    _ = _get_reactor_or_404(db, reactor_id)
    basic = db.get(m.Basic, basic_id)
    if not basic:
        raise HTTPException(status_code=404, detail="Basic not found")
    exists = (
        db.query(m.ReactorBasicJunction)
        .filter(and_(m.ReactorBasicJunction.reactor_id == reactor_id, m.ReactorBasicJunction.basic_id == basic_id))
        .first()
    )
    if not exists:
        db.add(m.ReactorBasicJunction(reactor_id=reactor_id, basic_id=basic_id))
        db.commit()
    return None


@router.delete("/{reactor_id}/basics/{basic_id}", status_code=204)
def unlink_basic(reactor_id: int, basic_id: int, db: DbSessionDep):
    exists = (
        db.query(m.ReactorBasicJunction)
        .filter(and_(m.ReactorBasicJunction.reactor_id == reactor_id, m.ReactorBasicJunction.basic_id == basic_id))
        .first()
    )
    if exists:
        db.delete(exists)
        db.commit()
    return None
