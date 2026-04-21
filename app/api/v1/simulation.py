"""Simulation execution and result query API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.database import SessionLocal
from app.engine.common import SimEvent
from app.engine.des_engine import run_des
from app.engine.line_balance import run_line_balance
from app.models.md import Equipment
from app.models.res import LineBalanceResult, SimulationResult, SimulationStateSnapshot
from app.models.sim import SimulationPlan
from app.schemas.res import (
    LineBalanceResultOut,
    RunStatusOut,
    SimEventOut,
    SimulationEventsOut,
    SimulationResultOut,
)

router = APIRouter(prefix="/plans", tags=["Simulation"])


# ---------------------------------------------------------------------------
# Background task — runs the simulation engines
# ---------------------------------------------------------------------------
def _execute_simulation(plan_id: str):
    """Background task: runs simulation engines with a dedicated DB session."""
    db = SessionLocal()
    try:
        plan = db.query(SimulationPlan).get(plan_id)
        result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
        if not plan or not result:
            return

        result.computation_start = datetime.utcnow()
        simulators = plan.enabled_simulators or []

        # Run line balance (static)
        if "LINE_BALANCE" in simulators:
            run_line_balance(db, plan_id)

        # Run DES (production process simulation)
        if "PRODUCTION" in simulators:
            des_metrics = run_des(db, plan_id)

            # Store the full event stream as a JSON summary in result_summary
            # (events are also accessible via the /events endpoint)
            result.result_summary = {
                "des_total_output": des_metrics.total_output,
                "des_ng_count": des_metrics.ng_count,
                "des_event_count": len(des_metrics.events),
                "des_duration_ms": int(float(plan.simulation_duration_hours) * 3600 * 1000),
                "hourly_output": des_metrics.hourly_output,
            }

        result.computation_status = "SUCCESS"
        result.computation_end = datetime.utcnow()
        plan.status = "COMPLETED"
        db.commit()

    except Exception as e:
        db.rollback()
        # Reload to avoid detached instance
        result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
        plan = db.query(SimulationPlan).get(plan_id)
        if result:
            result.computation_status = "FAILED"
            result.error_message = str(e)
        if plan:
            plan.status = "READY"  # Allow retry
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------
@router.post("/{plan_id}/run", response_model=RunStatusOut)
def run_simulation(
    plan_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    plan = db.query(SimulationPlan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status not in ("READY", "DRAFT"):
        raise HTTPException(400, f"Plan status must be READY or DRAFT to run, got {plan.status}")

    # Transition to RUNNING
    plan.status = "RUNNING"

    # Create result record
    existing = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if existing:
        # Clean up previous result
        db.query(SimulationStateSnapshot).filter(SimulationStateSnapshot.result_id == existing.result_id).delete()
        db.query(LineBalanceResult).filter(LineBalanceResult.result_id == existing.result_id).delete()
        db.delete(existing)
        db.flush()

    result = SimulationResult(
        result_id=str(uuid.uuid4()),
        plan_id=plan_id,
        computation_status="COMPUTING",
    )
    db.add(result)
    db.commit()

    # Run in background
    background_tasks.add_task(_execute_simulation, plan_id)

    return RunStatusOut(plan_id=plan_id, computation_status="COMPUTING")


# ---------------------------------------------------------------------------
# Run status
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/run/status", response_model=RunStatusOut)
def get_run_status(plan_id: str, db: Session = Depends(get_db)):
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise HTTPException(404, "No simulation result found")
    return RunStatusOut(plan_id=plan_id, computation_status=result.computation_status)


# ---------------------------------------------------------------------------
# Result summary
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/result", response_model=SimulationResultOut)
def get_result(plan_id: str, db: Session = Depends(get_db)):
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise HTTPException(404, "No simulation result found")
    return result


# ---------------------------------------------------------------------------
# Line balance results
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/result/line-balance", response_model=list[LineBalanceResultOut])
def get_line_balance_results(plan_id: str, db: Session = Depends(get_db)):
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise HTTPException(404, "No simulation result found")
    return (
        db.query(LineBalanceResult)
        .filter(LineBalanceResult.result_id == result.result_id)
        .all()
    )


# ---------------------------------------------------------------------------
# State snapshots (paginated, for chart data)
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/result/snapshots")
def get_snapshots(
    plan_id: str,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise HTTPException(404, "No simulation result found")

    snapshots = (
        db.query(SimulationStateSnapshot)
        .filter(SimulationStateSnapshot.result_id == result.result_id)
        .order_by(SimulationStateSnapshot.sim_timestamp_sec)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "sim_timestamp_sec": float(s.sim_timestamp_sec),
            "equipment_states": s.equipment_states,
            "wip_states": s.wip_states,
        }
        for s in snapshots
    ]


# ---------------------------------------------------------------------------
# Full event stream (for Kit / Omniverse 3D playback)
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/result/events", response_model=SimulationEventsOut)
def get_events(plan_id: str, db: Session = Depends(get_db)):
    """Return the full millisecond-precision event stream.

    This endpoint is consumed by the Omniverse Kit Data Bridge to drive
    3D animation of equipment models via creator_binding_id (prim paths).
    """
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise HTTPException(404, "No simulation result found")
    if result.computation_status != "SUCCESS":
        raise HTTPException(400, f"Simulation not completed: {result.computation_status}")

    plan = db.query(SimulationPlan).get(plan_id)
    duration_ms = int(float(plan.simulation_duration_hours) * 3600 * 1000)

    # Reconstruct events from state snapshots
    # For a full implementation, events would be stored in a dedicated table.
    # For now, we reconstruct from snapshots + result_summary
    snapshots = (
        db.query(SimulationStateSnapshot)
        .filter(SimulationStateSnapshot.result_id == result.result_id)
        .order_by(SimulationStateSnapshot.sim_timestamp_sec)
        .all()
    )

    events: list[SimEventOut] = []
    prev_states: dict[str, str] = {}

    for snap in snapshots:
        t_ms = int(float(snap.sim_timestamp_sec) * 1000)
        eq_states = snap.equipment_states or {}

        for eq_id, state_info in eq_states.items():
            current_status = state_info.get("status", "IDLE") if isinstance(state_info, dict) else str(state_info)
            prev_status = prev_states.get(eq_id)

            if current_status != prev_status:
                # Look up prim_path
                eq = db.query(Equipment).get(eq_id)
                prim_path = eq.creator_binding_id if eq else None

                event_type = current_status
                if current_status == "BUSY":
                    event_type = "PROCESSING_START"
                elif current_status == "IDLE" and prev_status == "BUSY":
                    event_type = "PROCESSING_END"
                elif current_status == "FAILURE":
                    event_type = "FAILURE_START"
                elif current_status == "IDLE" and prev_status == "FAILURE":
                    event_type = "FAILURE_END"

                events.append(SimEventOut(
                    timestamp_ms=t_ms,
                    equipment_id=eq_id,
                    prim_path=prim_path,
                    event_type=event_type,
                ))

            prev_states[eq_id] = current_status

    return SimulationEventsOut(
        plan_id=plan_id,
        total_events=len(events),
        duration_ms=duration_ms,
        events=events,
    )
