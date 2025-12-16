from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_

from ..dependencies import DbSessionDep
from .. import models as m
from ..schemas.reactors import ReactorCreate, ReactorRead, ReactorUpdate
from ..schemas.basics import BasicRead

router = APIRouter(prefix="/api/v1/reactors", tags=["v1: reactors"])


def _get_reactor_or_404(db: DbSessionDep, reactor_id: int) -> m.Reactor:
    obj = db.get(m.Reactor, reactor_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")
    return obj


def _get_reactor_by_name_or_404(db: DbSessionDep, name: str) -> m.Reactor:
    obj = db.query(m.Reactor).filter(m.Reactor.name == name).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Reactor not found")
    return obj


# NOTE: Listing reactors endpoint intentionally removed to simplify frontend usage per requirements.


@router.get("/{name}", response_model=ReactorRead)
def get_reactor(name: str, db: DbSessionDep):
    obj = _get_reactor_by_name_or_404(db, name)

    # Load associated basics via junction
    basics = (
        db.query(m.Basic)
        .join(m.ReactorBasicJunction, m.ReactorBasicJunction.basic_id == m.Basic.id)
        .filter(m.ReactorBasicJunction.reactor_id == obj.id)
        .all()
    )

    # Build input and utility sections from associated basics
    input_section: dict[str, dict] = {}
    utility_section: dict[str, dict] = {}

    for b in basics:
        usage = (b.usage or '').lower()
        if usage == "inlet":
            input_section[b.name] = {
                "type": b.type,
                "phases": b.phase or {},
                "source": [],
                "chemistry": {"reaction": []},
                "operation": b.operation or {},
                "structure": b.structure or {},
                "destination": ["reactor vessel"],
            }
        elif usage == "utilities":
            utility_section[b.name] = {
                "source": [],
                "operation": b.operation or {},
                "structure": b.structure or {},
                "destination": ["reactor vessel"],
            }

    # Compose flattened response from stored reactor block and computed sections
    reactor_block = obj.reactor or {}
    return {
        "id": obj.id,
        "name": obj.name,
        "number_of_input": obj.number_of_input,
        "number_of_output": obj.number_of_output,
        "icon_url": obj.icon_url,
        "reactor": reactor_block,
        "input": input_section,
        "utility": utility_section,
        "chemistry": obj.chemistry,
        "kinetics": obj.kinetics,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


@router.post("/", response_model=ReactorRead, status_code=201)
def create_reactor(payload: ReactorCreate, db: DbSessionDep):
    obj = m.Reactor(
        name=payload.name,
        number_of_input=payload.number_of_input or 0,
        number_of_output=payload.number_of_output or 0,
        icon_url=payload.icon_url,
        reactor=payload.reactor or {},
        chemistry=payload.chemistry,
        kinetics=payload.kinetics,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Build flattened response (likely with empty input/utility right after creation)
    return {
        "id": obj.id,
        "name": obj.name,
        "number_of_input": obj.number_of_input,
        "number_of_output": obj.number_of_output,
        "icon_url": obj.icon_url,
        "reactor": obj.reactor or {},
        "input": {},
        "utility": {},
        "chemistry": obj.chemistry,
        "kinetics": obj.kinetics,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


@router.patch("/{name}", response_model=ReactorRead)
def update_reactor(name: str, payload: ReactorUpdate, db: DbSessionDep):
    obj = _get_reactor_by_name_or_404(db, name)
    data = payload.model_dump(exclude_unset=True)
    # Update reactor block directly if provided
    if "reactor" in data:
        obj.reactor = data.pop("reactor") or {}
    for k, v in data.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Recompute input/utility from current associations
    basics = (
        db.query(m.Basic)
        .join(m.ReactorBasicJunction, m.ReactorBasicJunction.basic_id == m.Basic.id)
        .filter(m.ReactorBasicJunction.reactor_id == obj.id)
        .all()
    )
    input_section: dict[str, dict] = {}
    utility_section: dict[str, dict] = {}
    for b in basics:
        usage = (b.usage or '').lower()
        if usage == "inlet":
            input_section[b.name] = {
                "type": b.type,
                "phases": b.phase or {},
                "source": [],
                "chemistry": {"reaction": []},
                "operation": b.operation or {},
                "structure": b.structure or {},
                "destination": ["reactor vessel"],
            }
        elif usage == "utilities":
            utility_section[b.name] = {
                "source": [],
                "operation": b.operation or {},
                "structure": b.structure or {},
                "destination": ["reactor vessel"],
            }
    return {
        "id": obj.id,
        "name": obj.name,
        "number_of_input": obj.number_of_input,
        "number_of_output": obj.number_of_output,
        "icon_url": obj.icon_url,
        "reactor": obj.reactor or {},
        "input": input_section,
        "utility": utility_section,
        "chemistry": obj.chemistry,
        "kinetics": obj.kinetics,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


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
