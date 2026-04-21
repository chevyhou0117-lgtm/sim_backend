"""Pydantic schemas for master data API responses."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FactoryOut(BaseModel):
    factory_id: str
    factory_code: str
    factory_name: str
    location: str | None = None
    timezone: str
    status: str

    model_config = {"from_attributes": True}


class StageOut(BaseModel):
    stage_id: str
    factory_id: str
    stage_code: str
    stage_name: str
    sequence: int
    stage_type: str
    line_count: int | None = None
    status: str
    creator_binding_id: str | None = None

    model_config = {"from_attributes": True}


class ProductionLineOut(BaseModel):
    line_id: str
    stage_id: str
    line_code: str
    line_name: str
    smt_pph: Decimal | None = None
    operation_count: int | None = None
    status: str
    creator_binding_id: str | None = None

    model_config = {"from_attributes": True}


class OperationOut(BaseModel):
    operation_id: str
    stage_id: str
    operation_code: str
    operation_name: str
    sequence: int
    operation_type: str | None = None
    is_key_operation: bool | None = False
    status: str
    creator_binding_id: str | None = None

    model_config = {"from_attributes": True}


class EquipmentOut(BaseModel):
    equipment_id: str
    operation_id: str
    equipment_code: str
    equipment_name: str
    equipment_type: str
    manufacturer: str | None = None
    model_no: str | None = None
    standard_ct: Decimal | None = None
    status: str
    creator_binding_id: str | None = None

    model_config = {"from_attributes": True}


class BOPProcessOut(BaseModel):
    bop_process_id: str
    bop_id: str
    operation_id: str
    sequence: int
    standard_ct: Decimal
    panel_qty: int | None = None
    ct_per_panel: Decimal | None = None
    yield_rate: Decimal
    standard_worker_count: int
    min_worker_count: int | None = None
    primary_material_type: str | None = None

    model_config = {"from_attributes": True}


class BOPOut(BaseModel):
    bop_id: str
    product_id: str
    line_id: str
    bop_version: str
    is_active: bool
    processes: list[BOPProcessOut] = []

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    product_id: str
    product_code: str
    product_name: str
    product_category: str | None = None
    unit: str
    status: str

    model_config = {"from_attributes": True}


class OperationTransitionOut(BaseModel):
    transition_id: str
    bop_id: str
    from_operation_id: str
    to_operation_id: str
    transfer_time: Decimal
    mandatory_wait_time: Decimal
    transfer_mode: str | None = None
    wait_reason: str | None = None

    model_config = {"from_attributes": True}


class EquipmentFailureParamOut(BaseModel):
    param_id: str
    equipment_id: str
    mtbf_hours: Decimal
    mttr_minutes: Decimal
    failure_distribution: str | None = None
    data_source: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Aggregated views for config page panels
# ---------------------------------------------------------------------------
class LineEquipmentConfigItem(BaseModel):
    """Flattened equipment row joined with operation / line / stage info."""

    equipment_id: str
    equipment_code: str
    equipment_name: str
    equipment_type: str
    manufacturer: str | None = None
    model_no: str | None = None
    standard_ct: Decimal | None = None
    operation_id: str
    operation_code: str
    operation_name: str
    operation_sequence: int
    line_id: str
    line_code: str
    line_name: str
    stage_id: str
    stage_name: str


class LineEquipmentConfigOut(BaseModel):
    """Dedicated payload for the 产线设备配置 section on the plan config page."""

    factory_id: str
    line_count: int
    operation_count: int
    equipment_count: int
    last_updated: datetime | None = None
    items: list[LineEquipmentConfigItem]
