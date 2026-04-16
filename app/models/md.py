"""Base data layer models (md_ prefix) — read-only cache from master data platform."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# md_factory
# ---------------------------------------------------------------------------
class Factory(Base):
    __tablename__ = "md_factory"

    factory_id = Column(String(36), primary_key=True, default=_uuid)
    factory_code = Column(String(50), nullable=False, unique=True)
    factory_name = Column(String(200), nullable=False)
    location = Column(String(500))
    timezone = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    stages = relationship("Stage", back_populates="factory")
    warehouses = relationship("Warehouse", back_populates="factory")
    work_calendars = relationship("WorkCalendar", back_populates="factory")
    worker_types = relationship("WorkerType", back_populates="factory")


# ---------------------------------------------------------------------------
# md_stage
# ---------------------------------------------------------------------------
class Stage(Base):
    __tablename__ = "md_stage"

    stage_id = Column(String(36), primary_key=True, default=_uuid)
    factory_id = Column(String(36), ForeignKey("md_factory.factory_id"), nullable=False)
    stage_code = Column(String(50), nullable=False)
    stage_name = Column(String(200), nullable=False)
    sequence = Column(Integer, nullable=False)
    stage_type = Column(String(50), nullable=False)
    line_count = Column(Integer)
    status = Column(String(20), nullable=False, default="ACTIVE")
    creator_binding_id = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("factory_id", "stage_code"),)

    factory = relationship("Factory", back_populates="stages")
    production_lines = relationship("ProductionLine", back_populates="stage")


# ---------------------------------------------------------------------------
# md_production_line
# ---------------------------------------------------------------------------
class ProductionLine(Base):
    __tablename__ = "md_production_line"

    line_id = Column(String(36), primary_key=True, default=_uuid)
    stage_id = Column(String(36), ForeignKey("md_stage.stage_id"), nullable=False)
    line_code = Column(String(50), nullable=False)
    line_name = Column(String(200), nullable=False)
    smt_pph = Column(Numeric(10, 2))
    operation_count = Column(Integer)
    status = Column(String(20), nullable=False, default="ACTIVE")
    sort_order = Column(Integer)
    creator_binding_id = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("stage_id", "line_code"),)

    stage = relationship("Stage", back_populates="production_lines")
    operations = relationship("Operation", back_populates="production_line")
    wip_buffers = relationship("WIPBuffer", back_populates="production_line")
    bops = relationship("BOP", back_populates="production_line")


# ---------------------------------------------------------------------------
# md_operation
# ---------------------------------------------------------------------------
class Operation(Base):
    __tablename__ = "md_operation"

    operation_id = Column(String(36), primary_key=True, default=_uuid)
    line_id = Column(String(36), ForeignKey("md_production_line.line_id"), nullable=False)
    operation_code = Column(String(50), nullable=False)
    operation_name = Column(String(200), nullable=False)
    sequence = Column(Integer, nullable=False)
    operation_type = Column(String(50))
    is_key_operation = Column(Boolean, default=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    creator_binding_id = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("line_id", "operation_code"),)

    production_line = relationship("ProductionLine", back_populates="operations")
    equipments = relationship("Equipment", back_populates="operation")
    staffing_configs = relationship("StaffingConfig", back_populates="operation")


# ---------------------------------------------------------------------------
# md_equipment
# ---------------------------------------------------------------------------
class Equipment(Base):
    __tablename__ = "md_equipment"

    equipment_id = Column(String(36), primary_key=True, default=_uuid)
    operation_id = Column(String(36), ForeignKey("md_operation.operation_id"), nullable=False)
    equipment_code = Column(String(50), nullable=False)
    equipment_name = Column(String(200), nullable=False)
    equipment_type = Column(String(50), nullable=False)
    manufacturer = Column(String(200))
    model_no = Column(String(100))
    standard_ct = Column(Numeric(10, 3))
    status = Column(String(20), nullable=False, default="ACTIVE")
    sort_order = Column(Integer)
    creator_binding_id = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # equipment_code is unique within factory scope — enforced at app level
    # (cross-table FK to factory requires join through operation→line→stage→factory)

    operation = relationship("Operation", back_populates="equipments")
    failure_param = relationship("EquipmentFailureParam", back_populates="equipment", uselist=False)


# ---------------------------------------------------------------------------
# md_equipment_failure_param
# ---------------------------------------------------------------------------
class EquipmentFailureParam(Base):
    __tablename__ = "md_equipment_failure_param"

    param_id = Column(String(36), primary_key=True, default=_uuid)
    equipment_id = Column(String(36), ForeignKey("md_equipment.equipment_id"), nullable=False, unique=True)
    mtbf_hours = Column(Numeric(10, 2), nullable=False)
    mttr_minutes = Column(Numeric(10, 2), nullable=False)
    failure_distribution = Column(String(20), default="EXPONENTIAL")
    data_source = Column(String(100))
    effective_date = Column(Date)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    equipment = relationship("Equipment", back_populates="failure_param")


# ---------------------------------------------------------------------------
# md_wip_buffer
# ---------------------------------------------------------------------------
class WIPBuffer(Base):
    __tablename__ = "md_wip_buffer"

    wip_id = Column(String(36), primary_key=True, default=_uuid)
    line_id = Column(String(36), ForeignKey("md_production_line.line_id"), nullable=False)
    wip_code = Column(String(50), nullable=False)
    wip_name = Column(String(200), nullable=False)
    capacity_volume = Column(Numeric(15, 3), nullable=False)
    capacity_qty = Column(Integer)
    pre_operation_id = Column(String(36), ForeignKey("md_operation.operation_id"))
    post_operation_id = Column(String(36), ForeignKey("md_operation.operation_id"))
    location = Column(String(200))
    creator_binding_id = Column(String(100))
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    production_line = relationship("ProductionLine", back_populates="wip_buffers")
    pre_operation = relationship("Operation", foreign_keys=[pre_operation_id])
    post_operation = relationship("Operation", foreign_keys=[post_operation_id])


# ---------------------------------------------------------------------------
# md_warehouse
# ---------------------------------------------------------------------------
class Warehouse(Base):
    __tablename__ = "md_warehouse"

    warehouse_id = Column(String(36), primary_key=True, default=_uuid)
    factory_id = Column(String(36), ForeignKey("md_factory.factory_id"), nullable=False)
    warehouse_code = Column(String(50), nullable=False)
    warehouse_name = Column(String(200), nullable=False)
    warehouse_type = Column(String(30), nullable=False)
    location = Column(String(200))
    total_capacity = Column(Numeric(15, 3))
    creator_binding_id = Column(String(100))
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    factory = relationship("Factory", back_populates="warehouses")


# ---------------------------------------------------------------------------
# md_product
# ---------------------------------------------------------------------------
class Product(Base):
    __tablename__ = "md_product"

    product_id = Column(String(36), primary_key=True, default=_uuid)
    product_code = Column(String(50), nullable=False, unique=True)
    product_name = Column(String(200), nullable=False)
    product_category = Column(String(50))
    unit = Column(String(20), nullable=False)
    standard_changeover_time = Column(Numeric(10, 2))
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    bops = relationship("BOP", back_populates="product")


# ---------------------------------------------------------------------------
# md_bop
# ---------------------------------------------------------------------------
class BOP(Base):
    __tablename__ = "md_bop"

    bop_id = Column(String(36), primary_key=True, default=_uuid)
    product_id = Column(String(36), ForeignKey("md_product.product_id"), nullable=False)
    line_id = Column(String(36), ForeignKey("md_production_line.line_id"), nullable=False)
    bop_version = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    effective_date = Column(Date)
    created_by = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Only one active BOP per (product, line)
    # Enforced at application level (partial unique index not portable)

    product = relationship("Product", back_populates="bops")
    production_line = relationship("ProductionLine", back_populates="bops")
    processes = relationship("BOPProcess", back_populates="bop", order_by="BOPProcess.sequence")
    transitions = relationship("OperationTransition", back_populates="bop")


# ---------------------------------------------------------------------------
# md_bop_process
# ---------------------------------------------------------------------------
class BOPProcess(Base):
    __tablename__ = "md_bop_process"

    bop_process_id = Column(String(36), primary_key=True, default=_uuid)
    bop_id = Column(String(36), ForeignKey("md_bop.bop_id"), nullable=False)
    operation_id = Column(String(36), ForeignKey("md_operation.operation_id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    standard_ct = Column(Numeric(10, 3), nullable=False)
    panel_qty = Column(Integer)
    ct_per_panel = Column(Numeric(10, 3))
    yield_rate = Column(Numeric(5, 4), nullable=False, default=1.0)
    standard_worker_count = Column(Integer, nullable=False, default=0)
    min_worker_count = Column(Integer)
    primary_material_type = Column(String(100))
    sop_ref = Column(String(500))
    sop_content = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("bop_id", "sequence"),)

    bop = relationship("BOP", back_populates="processes")
    operation = relationship("Operation")
    params = relationship("BOPProcessParam", back_populates="bop_process")
    ng_types = relationship("BOPProcessNGType", back_populates="bop_process")


# ---------------------------------------------------------------------------
# md_bop_process_param
# ---------------------------------------------------------------------------
class BOPProcessParam(Base):
    __tablename__ = "md_bop_process_param"

    param_id = Column(String(36), primary_key=True, default=_uuid)
    bop_process_id = Column(String(36), ForeignKey("md_bop_process.bop_process_id"), nullable=False)
    param_name = Column(String(200), nullable=False)
    param_value = Column(String(200))
    upper_limit = Column(String(100))
    lower_limit = Column(String(100))
    sequence = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    bop_process = relationship("BOPProcess", back_populates="params")


# ---------------------------------------------------------------------------
# md_bop_process_ng_type
# ---------------------------------------------------------------------------
class BOPProcessNGType(Base):
    __tablename__ = "md_bop_process_ng_type"

    id = Column(String(36), primary_key=True, default=_uuid)
    bop_process_id = Column(String(36), ForeignKey("md_bop_process.bop_process_id"), nullable=False)
    ng_code = Column(String(20), ForeignKey("md_ng_type.ng_code"), nullable=False)
    occurrence_rate = Column(Numeric(5, 4))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    bop_process = relationship("BOPProcess", back_populates="ng_types")
    ng_type = relationship("NGType")


# ---------------------------------------------------------------------------
# md_operation_transition
# ---------------------------------------------------------------------------
class OperationTransition(Base):
    __tablename__ = "md_operation_transition"

    transition_id = Column(String(36), primary_key=True, default=_uuid)
    bop_id = Column(String(36), ForeignKey("md_bop.bop_id"), nullable=False)
    from_operation_id = Column(String(36), ForeignKey("md_operation.operation_id"), nullable=False)
    to_operation_id = Column(String(36), ForeignKey("md_operation.operation_id"), nullable=False)
    transfer_time = Column(Numeric(10, 3), nullable=False, default=0)
    mandatory_wait_time = Column(Numeric(10, 3), nullable=False, default=0)
    transfer_mode = Column(String(30))
    wait_reason = Column(String(200))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    bop = relationship("BOP", back_populates="transitions")
    from_operation = relationship("Operation", foreign_keys=[from_operation_id])
    to_operation = relationship("Operation", foreign_keys=[to_operation_id])


# ---------------------------------------------------------------------------
# md_work_calendar
# ---------------------------------------------------------------------------
class WorkCalendar(Base):
    __tablename__ = "md_work_calendar"

    calendar_id = Column(String(36), primary_key=True, default=_uuid)
    factory_id = Column(String(36), ForeignKey("md_factory.factory_id"), nullable=False)
    calendar_date = Column(Date, nullable=False)
    is_working_day = Column(Boolean, nullable=False)
    day_type = Column(String(20), nullable=False)
    total_work_hours = Column(Numeric(5, 2))
    remarks = Column(String(200))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    factory = relationship("Factory", back_populates="work_calendars")
    shifts = relationship("Shift", back_populates="calendar")


# ---------------------------------------------------------------------------
# md_shift
# ---------------------------------------------------------------------------
class Shift(Base):
    __tablename__ = "md_shift"

    shift_id = Column(String(36), primary_key=True, default=_uuid)
    calendar_id = Column(String(36), ForeignKey("md_work_calendar.calendar_id"), nullable=False)
    shift_name = Column(String(50), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    work_hours = Column(Numeric(5, 2), nullable=False)
    break_minutes = Column(Integer)
    shift_order = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    calendar = relationship("WorkCalendar", back_populates="shifts")


# ---------------------------------------------------------------------------
# md_worker_type
# ---------------------------------------------------------------------------
class WorkerType(Base):
    __tablename__ = "md_worker_type"

    worker_type_id = Column(String(36), primary_key=True, default=_uuid)
    factory_id = Column(String(36), ForeignKey("md_factory.factory_id"), nullable=False)
    worker_type_code = Column(String(50), nullable=False)
    worker_type_name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    factory = relationship("Factory", back_populates="worker_types")


# ---------------------------------------------------------------------------
# md_staffing_config
# ---------------------------------------------------------------------------
class StaffingConfig(Base):
    __tablename__ = "md_staffing_config"

    staffing_id = Column(String(36), primary_key=True, default=_uuid)
    operation_id = Column(String(36), ForeignKey("md_operation.operation_id"), nullable=False)
    worker_type_id = Column(String(36), ForeignKey("md_worker_type.worker_type_id"), nullable=False)
    worker_count = Column(Integer, nullable=False)
    ct_with_this_count = Column(Numeric(10, 3), nullable=False)
    is_standard = Column(Boolean, nullable=False, default=True)
    effective_date = Column(Date)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    operation = relationship("Operation", back_populates="staffing_configs")
    worker_type = relationship("WorkerType")


# ---------------------------------------------------------------------------
# md_material
# ---------------------------------------------------------------------------
class Material(Base):
    __tablename__ = "md_material"

    material_id = Column(String(36), primary_key=True, default=_uuid)
    material_code = Column(String(50), nullable=False, unique=True)
    material_name = Column(String(200), nullable=False)
    material_type = Column(String(30), nullable=False)
    smt_placement_points = Column(Integer)
    unit = Column(String(20), nullable=False)
    unit_volume = Column(Numeric(15, 6))
    unit_weight = Column(Numeric(10, 3))
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# md_ng_type
# ---------------------------------------------------------------------------
class NGType(Base):
    __tablename__ = "md_ng_type"

    ng_code = Column(String(20), primary_key=True)
    ng_name = Column(String(100), nullable=False)
    impact_level = Column(String(10), nullable=False)
    repairable = Column(String(20), nullable=False)
    repair_time_sec = Column(Numeric(10, 2), nullable=False)
    repair_rate = Column(Numeric(5, 4), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
