"""Pydantic schemas for simulation result API responses."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SimulationResultOut(BaseModel):
    result_id: str
    plan_id: str
    computation_status: str
    computation_start: datetime | None = None
    computation_end: datetime | None = None
    total_output: int | None = None
    output_per_hour: Decimal | None = None
    overall_lbr: Decimal | None = None
    bottleneck_equipment_id: str | None = None
    bottleneck_utilization: Decimal | None = None
    material_shortage_count: int | None = None
    equipment_failure_count: int | None = None
    result_summary: dict | None = None

    model_config = {"from_attributes": True}


class LineBalanceResultOut(BaseModel):
    lb_result_id: str
    result_id: str
    line_id: str
    takt_time: Decimal
    lbr: Decimal
    balance_loss_rate: Decimal
    bottleneck_operation_id: str | None = None
    bottleneck_ct: Decimal | None = None
    idle_operation_id: str | None = None
    operation_load_detail: dict | None = None
    workshop_load_rate: Decimal | None = None
    factory_load_rate: Decimal | None = None

    model_config = {"from_attributes": True}


class SimEventOut(BaseModel):
    timestamp_ms: int
    equipment_id: str
    prim_path: str | None = None
    event_type: str
    product_id: str | None = None
    metadata: dict | None = None


class SimulationEventsOut(BaseModel):
    plan_id: str
    total_events: int
    duration_ms: int
    events: list[SimEventOut]


class RunStatusOut(BaseModel):
    plan_id: str
    computation_status: str
    progress_pct: float | None = None
