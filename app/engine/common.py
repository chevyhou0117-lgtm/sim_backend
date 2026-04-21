"""Shared utilities for simulation engines — CT resolution, data loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.md import BOP, BOPProcess, Equipment, Operation, StaffingConfig
from app.models.sim import ParameterOverride, SoftConstraintConfig


@dataclass
class ResolvedProcess:
    """A BOP process with its effective CT and equipment info resolved."""

    bop_process_id: str
    operation_id: str
    operation_name: str
    sequence: int
    effective_ct: float  # seconds
    equipment_count: int  # number of parallel machines
    equipment_ids: list[str]
    equipment_prim_paths: list[str]  # creator_binding_id values
    yield_rate: float
    worker_count: int
    design_ct: float  # BOP standard_ct before overrides


@dataclass
class SimEvent:
    """A single simulation event with millisecond precision."""

    timestamp_ms: int
    equipment_id: str
    prim_path: str | None
    event_type: str  # PROCESSING_START / PROCESSING_END / IDLE / FAILURE_START / FAILURE_END / BLOCKED
    product_id: str | None = None
    metadata: dict | None = None


def get_enabled_constraints(db: Session, plan_id: str) -> set[str]:
    """Return set of enabled constraint types for a plan."""
    rows = (
        db.query(SoftConstraintConfig)
        .filter(SoftConstraintConfig.plan_id == plan_id, SoftConstraintConfig.is_enabled == True)  # noqa: E712
        .all()
    )
    return {r.constraint_type for r in rows}


def resolve_ct_for_operation(
    db: Session,
    plan_id: str,
    operation_id: str,
    bop_standard_ct: float,
    sim_time_hours: float | None = None,
) -> float:
    """Resolve effective CT for an operation considering parameter overrides.

    Override priority: EQUIPMENT > OPERATION > LINE > GLOBAL > BOP standard CT.
    """
    # Query all relevant overrides for this plan, ordered by specificity
    overrides = (
        db.query(ParameterOverride)
        .filter(ParameterOverride.plan_id == plan_id, ParameterOverride.param_key == "ct_override")
        .all()
    )

    # Get the operation's equipment for EQUIPMENT-scope matching
    equipment_ids = [
        e.equipment_id
        for e in db.query(Equipment).filter(Equipment.operation_id == operation_id).all()
    ]

    # Operation no longer has line_id (now stage_id). Derive line_id via BOPProcess → BOP.
    bop_row = (
        db.query(BOP.line_id)
        .join(BOPProcess, BOPProcess.bop_id == BOP.bop_id)
        .filter(BOPProcess.operation_id == operation_id, BOP.is_active == True)  # noqa: E712
        .first()
    )
    line_id = bop_row[0] if bop_row else None

    best_ct = None
    best_priority = 99  # lower = more specific

    SCOPE_PRIORITY = {"EQUIPMENT": 0, "OPERATION": 1, "LINE": 2, "GLOBAL": 4}

    for ov in overrides:
        priority = SCOPE_PRIORITY.get(ov.scope_type, 99)

        # Check scope match
        if ov.scope_type == "EQUIPMENT" and ov.scope_id not in equipment_ids:
            continue
        if ov.scope_type == "OPERATION" and ov.scope_id != operation_id:
            continue
        if ov.scope_type == "LINE" and ov.scope_id != line_id:
            continue

        # Check time range
        if sim_time_hours is not None:
            if ov.time_range_start is not None and sim_time_hours < float(ov.time_range_start):
                continue
            if ov.time_range_end is not None and sim_time_hours > float(ov.time_range_end):
                continue

        if priority < best_priority:
            best_priority = priority
            best_ct = float(ov.param_value)

    if best_ct is not None:
        return best_ct

    # Check efficiency override
    efficiency_overrides = (
        db.query(ParameterOverride)
        .filter(ParameterOverride.plan_id == plan_id, ParameterOverride.param_key == "efficiency")
        .all()
    )
    for ov in efficiency_overrides:
        if ov.scope_type == "GLOBAL" or (ov.scope_type == "OPERATION" and ov.scope_id == operation_id):
            eff = float(ov.param_value)
            if eff > 0:
                return bop_standard_ct / eff

    return bop_standard_ct


def load_resolved_processes(db: Session, plan_id: str, line_id: str) -> list[ResolvedProcess]:
    """Load BOP processes for a line with resolved CTs and equipment info."""
    bop = (
        db.query(BOP)
        .filter(BOP.line_id == line_id, BOP.is_active == True)  # noqa: E712
        .first()
    )
    if not bop:
        return []

    processes = (
        db.query(BOPProcess)
        .filter(BOPProcess.bop_id == bop.bop_id)
        .order_by(BOPProcess.sequence)
        .all()
    )

    result = []
    for proc in processes:
        operation = db.query(Operation).get(proc.operation_id)
        equipments = (
            db.query(Equipment)
            .filter(Equipment.operation_id == proc.operation_id, Equipment.status == "ACTIVE")
            .all()
        )

        effective_ct = resolve_ct_for_operation(
            db, plan_id, proc.operation_id, float(proc.standard_ct)
        )

        result.append(
            ResolvedProcess(
                bop_process_id=proc.bop_process_id,
                operation_id=proc.operation_id,
                operation_name=operation.operation_name if operation else "Unknown",
                sequence=proc.sequence,
                effective_ct=effective_ct,
                equipment_count=max(len(equipments), 1),
                equipment_ids=[e.equipment_id for e in equipments],
                equipment_prim_paths=[e.creator_binding_id or "" for e in equipments],
                yield_rate=float(proc.yield_rate),
                worker_count=proc.standard_worker_count,
                design_ct=float(proc.standard_ct),
            )
        )

    return result
