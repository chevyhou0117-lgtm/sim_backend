"""Simulation plan CRUD API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.biz import ProductionTask
from app.models.res import LineBalanceResult, SimulationResult, SimulationStateSnapshot
from app.models.sim import (
    AnomalyInjection,
    ParameterOverride,
    SimulationPlan,
    SoftConstraintConfig,
)
from app.schemas.sim import (
    AnomalyCreate,
    AnomalyOut,
    AnomalyUpdate,
    BatchIds,
    ConstraintOut,
    ConstraintSet,
    OverrideCreate,
    OverrideOut,
    PlanCreate,
    PlanOut,
    PlanUpdate,
    TaskCreate,
    TaskOut,
)

router = APIRouter(prefix="/plans", tags=["Simulation Plans"])


def _get_plan(db: Session, plan_id: str) -> SimulationPlan:
    plan = db.query(SimulationPlan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------
@router.get("", response_model=list[PlanOut])
def list_plans(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(SimulationPlan)
    if status:
        q = q.filter(SimulationPlan.status == status)
    return q.order_by(SimulationPlan.updated_at.desc()).all()


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(body: PlanCreate, db: Session = Depends(get_db)):
    plan = SimulationPlan(
        plan_name=body.plan_name,
        factory_id=body.factory_id,
        enabled_simulators=body.enabled_simulators,
        simulation_duration_hours=body.simulation_duration_hours,
        plan_description=body.plan_description,
        created_by=body.created_by,
        status="DRAFT",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    return _get_plan(db, plan_id)


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: str, body: PlanUpdate, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if plan.status not in ("DRAFT", "READY"):
        raise HTTPException(400, "Can only update DRAFT or READY plans")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if plan.status != "DRAFT":
        raise HTTPException(400, "Can only delete DRAFT plans")
    db.delete(plan)
    db.commit()


# ---------------------------------------------------------------------------
# Soft Constraints
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/constraints", response_model=list[ConstraintOut])
def list_constraints(plan_id: str, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    return db.query(SoftConstraintConfig).filter(SoftConstraintConfig.plan_id == plan_id).all()


@router.post("/{plan_id}/constraints", response_model=ConstraintOut, status_code=201)
def set_constraint(plan_id: str, body: ConstraintSet, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    existing = (
        db.query(SoftConstraintConfig)
        .filter(SoftConstraintConfig.plan_id == plan_id, SoftConstraintConfig.constraint_type == body.constraint_type)
        .first()
    )
    if existing:
        existing.is_enabled = body.is_enabled
        db.commit()
        db.refresh(existing)
        return existing
    c = SoftConstraintConfig(plan_id=plan_id, constraint_type=body.constraint_type, is_enabled=body.is_enabled)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Parameter Overrides
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/overrides", response_model=list[OverrideOut])
def list_overrides(plan_id: str, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    return db.query(ParameterOverride).filter(ParameterOverride.plan_id == plan_id).all()


@router.post("/{plan_id}/overrides", response_model=OverrideOut, status_code=201)
def create_override(plan_id: str, body: OverrideCreate, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    o = ParameterOverride(plan_id=plan_id, **body.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/{plan_id}/overrides/{override_id}", status_code=204)
def delete_override(plan_id: str, override_id: str, db: Session = Depends(get_db)):
    o = db.query(ParameterOverride).get(override_id)
    if not o or o.plan_id != plan_id:
        raise HTTPException(404, "Override not found")
    db.delete(o)
    db.commit()


# ---------------------------------------------------------------------------
# Production Tasks
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/tasks", response_model=list[TaskOut])
def list_tasks(plan_id: str, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    return (
        db.query(ProductionTask)
        .filter(ProductionTask.plan_id == plan_id)
        .order_by(ProductionTask.production_sequence)
        .all()
    )


@router.post("/{plan_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(plan_id: str, body: TaskCreate, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    t = ProductionTask(plan_id=plan_id, **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# Anomaly Injection
# ---------------------------------------------------------------------------
@router.get("/{plan_id}/anomalies", response_model=list[AnomalyOut])
def list_anomalies(plan_id: str, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    return db.query(AnomalyInjection).filter(AnomalyInjection.plan_id == plan_id).all()


@router.post("/{plan_id}/anomalies", response_model=AnomalyOut, status_code=201)
def create_anomaly(plan_id: str, body: AnomalyCreate, db: Session = Depends(get_db)):
    _get_plan(db, plan_id)
    a = AnomalyInjection(plan_id=plan_id, **body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.patch("/{plan_id}/anomalies/{anomaly_id}", response_model=AnomalyOut)
def update_anomaly(plan_id: str, anomaly_id: str, body: AnomalyUpdate, db: Session = Depends(get_db)):
    a = db.query(AnomalyInjection).get(anomaly_id)
    if not a or a.plan_id != plan_id:
        raise HTTPException(404, "Anomaly not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{plan_id}/anomalies/{anomaly_id}", status_code=204)
def delete_anomaly(plan_id: str, anomaly_id: str, db: Session = Depends(get_db)):
    a = db.query(AnomalyInjection).get(anomaly_id)
    if not a or a.plan_id != plan_id:
        raise HTTPException(404, "Anomaly not found")
    db.delete(a)
    db.commit()


# ---------------------------------------------------------------------------
# Task Delete
# ---------------------------------------------------------------------------
@router.delete("/{plan_id}/tasks/{task_id}", status_code=204)
def delete_task(plan_id: str, task_id: str, db: Session = Depends(get_db)):
    t = db.query(ProductionTask).get(task_id)
    if not t or t.plan_id != plan_id:
        raise HTTPException(404, "Task not found")
    db.delete(t)
    db.commit()


# ---------------------------------------------------------------------------
# Archive / Copy / Cancel
# ---------------------------------------------------------------------------
@router.post("/{plan_id}/archive", response_model=PlanOut)
def archive_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if plan.status not in ("COMPLETED", "DRAFT", "READY"):
        raise HTTPException(400, f"Cannot archive plan in {plan.status} status")
    plan.status = "ARCHIVED"
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/copy", response_model=PlanOut)
def copy_plan(plan_id: str, db: Session = Depends(get_db)):
    src = _get_plan(db, plan_id)
    new_id = str(uuid.uuid4())
    new_plan = SimulationPlan(
        plan_id=new_id,
        plan_name=f"{src.plan_name} (Copy)",
        plan_description=src.plan_description,
        factory_id=src.factory_id,
        status="DRAFT",
        enabled_simulators=src.enabled_simulators,
        simulation_duration_hours=src.simulation_duration_hours,
        created_by=src.created_by,
    )
    db.add(new_plan)

    # Copy constraints
    for c in db.query(SoftConstraintConfig).filter(SoftConstraintConfig.plan_id == plan_id).all():
        db.add(SoftConstraintConfig(
            constraint_id=str(uuid.uuid4()), plan_id=new_id,
            constraint_type=c.constraint_type, is_enabled=c.is_enabled,
        ))

    # Copy overrides
    for o in db.query(ParameterOverride).filter(ParameterOverride.plan_id == plan_id).all():
        db.add(ParameterOverride(
            override_id=str(uuid.uuid4()), plan_id=new_id,
            scope_type=o.scope_type, scope_id=o.scope_id,
            param_key=o.param_key, param_value=o.param_value,
            time_range_start=o.time_range_start, time_range_end=o.time_range_end,
        ))

    # Copy tasks
    for t in db.query(ProductionTask).filter(ProductionTask.plan_id == plan_id).all():
        db.add(ProductionTask(
            task_id=str(uuid.uuid4()), plan_id=new_id,
            wo_id=None, stage_id=t.stage_id, line_id=t.line_id,
            product_code=t.product_code, plan_quantity=t.plan_quantity,
            production_sequence=t.production_sequence, data_source="MANUAL_IMPORT",
        ))

    # Copy anomalies
    for a in db.query(AnomalyInjection).filter(AnomalyInjection.plan_id == plan_id).all():
        db.add(AnomalyInjection(
            anomaly_id=str(uuid.uuid4()), plan_id=new_id,
            anomaly_type=a.anomaly_type, target_id=a.target_id,
            start_sim_hour=a.start_sim_hour, duration_minutes=a.duration_minutes,
            description=a.description,
        ))

    db.commit()
    db.refresh(new_plan)
    return new_plan


@router.post("/{plan_id}/cancel", response_model=PlanOut)
def cancel_simulation(plan_id: str, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    if plan.status != "RUNNING":
        raise HTTPException(400, "Plan is not running")
    plan.status = "READY"
    # Clean up incomplete result
    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if result and result.computation_status == "COMPUTING":
        result.computation_status = "FAILED"
        result.error_message = "Cancelled by user"
    db.commit()
    db.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------
@router.post("/batch-archive")
def batch_archive(body: BatchIds, db: Session = Depends(get_db)):
    count = 0
    for pid in body.plan_ids:
        plan = db.query(SimulationPlan).get(pid)
        if plan and plan.status in ("COMPLETED", "DRAFT", "READY"):
            plan.status = "ARCHIVED"
            count += 1
    db.commit()
    return {"archived": count}


@router.post("/batch-delete")
def batch_delete(body: BatchIds, db: Session = Depends(get_db)):
    count = 0
    for pid in body.plan_ids:
        plan = db.query(SimulationPlan).get(pid)
        if plan and plan.status == "DRAFT":
            db.delete(plan)
            count += 1
    db.commit()
    return {"deleted": count}
