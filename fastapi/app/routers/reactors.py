from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..dependencies import DbSessionDep
from ..models.reactor import Reactor
from ..schemas.reactor import ReactorCreate, ReactorUpdate, ReactorRead

router = APIRouter(prefix="/models/reactors", tags=["models", "reactors"])


@router.get("/", response_model=List[ReactorRead])
def list_reactors(db: DbSessionDep, limit: int = Query(100, ge=0, le=500), offset: int = Query(0, ge=0)):
    q = db.query(Reactor).order_by(Reactor.id.desc()).offset(offset)
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/{reactor_id}", response_model=ReactorRead)
def get_reactor(reactor_id: int, db: DbSessionDep):
    obj = db.get(Reactor, reactor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")
    return obj


@router.post("/", response_model=ReactorRead, status_code=201)
def create_reactor(payload: ReactorCreate, db: DbSessionDep):
    obj = Reactor(
        name=payload.name,
        number_of_input=payload.number_of_input,
        number_of_output=payload.number_of_output,
        icon=payload.icon,
        species=payload.species,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{reactor_id}", response_model=ReactorRead)
def update_reactor(reactor_id: int, payload: ReactorUpdate, db: DbSessionDep):
    obj: Optional[Reactor] = db.get(Reactor, reactor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{reactor_id}", status_code=204)
def delete_reactor(reactor_id: int, db: DbSessionDep):
    obj: Optional[Reactor] = db.get(Reactor, reactor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")
    db.delete(obj)
    db.commit()
    return None
