"""Pydantic schemas for simulation plan API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# SimulationPlan
# ---------------------------------------------------------------------------
class PlanCreate(BaseModel):
    plan_name: str
    factory_id: str
    enabled_simulators: list[str]
    simulation_duration_hours: float
    plan_description: str | None = None
    created_by: str


class PlanUpdate(BaseModel):
    plan_name: str | None = None
    plan_description: str | None = None
    enabled_simulators: list[str] | None = None
    simulation_duration_hours: float | None = None


class PlanOut(BaseModel):
    plan_id: str
    plan_name: str
    plan_description: str | None = None
    factory_id: str
    status: str
    enabled_simulators: list[str]
    simulation_duration_hours: Decimal
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SoftConstraintConfig
# ---------------------------------------------------------------------------
class ConstraintSet(BaseModel):
    constraint_type: str
    is_enabled: bool


class ConstraintOut(BaseModel):
    constraint_id: str
    plan_id: str
    constraint_type: str
    is_enabled: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ParameterOverride
# ---------------------------------------------------------------------------
class OverrideCreate(BaseModel):
    scope_type: str
    scope_id: str | None = None
    param_key: str
    param_value: str
    time_range_start: float | None = None
    time_range_end: float | None = None


class OverrideOut(BaseModel):
    override_id: str
    plan_id: str
    scope_type: str
    scope_id: str | None = None
    param_key: str
    param_value: str
    time_range_start: Decimal | None = None
    time_range_end: Decimal | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ProductionTask
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    wo_id: str | None = None
    stage_id: str
    line_id: str
    product_code: str
    plan_quantity: int
    production_sequence: int
    data_source: str = "MANUAL_IMPORT"


class TaskOut(BaseModel):
    task_id: str
    plan_id: str
    wo_id: str | None = None
    stage_id: str
    line_id: str
    product_code: str
    plan_quantity: int
    completed_qty: int | None = None
    production_sequence: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AnomalyInjection
# ---------------------------------------------------------------------------
class AnomalyCreate(BaseModel):
    anomaly_type: str
    target_id: str
    start_sim_hour: float
    duration_minutes: float
    description: str | None = None


class AnomalyUpdate(BaseModel):
    anomaly_type: str | None = None
    target_id: str | None = None
    start_sim_hour: float | None = None
    duration_minutes: float | None = None
    description: str | None = None


class AnomalyOut(BaseModel):
    anomaly_id: str
    plan_id: str
    anomaly_type: str
    target_id: str
    start_sim_hour: Decimal
    duration_minutes: Decimal
    description: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Plan Version
# ---------------------------------------------------------------------------
class VersionCreate(BaseModel):
    version_name: str
    notes: str | None = None


class VersionOut(BaseModel):
    version_id: str
    plan_id: str
    version_name: str
    version_no: int
    is_baseline: bool
    key_metrics: dict | None = None
    notes: str | None = None
    archived_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Parameter Template
# ---------------------------------------------------------------------------
class TemplateCreate(BaseModel):
    template_name: str
    template_description: str | None = None
    factory_id: str | None = None
    is_public: bool = True
    template_content: dict
    created_by: str


class TemplateOut(BaseModel):
    template_id: str
    template_name: str
    template_type: str
    template_description: str | None = None
    factory_id: str | None = None
    is_public: bool
    template_content: dict
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
class ExportRequest(BaseModel):
    modules: list[str]
    format: str = "json"
    title: str | None = None
    language: str = "en"


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------
class BatchIds(BaseModel):
    plan_ids: list[str]
