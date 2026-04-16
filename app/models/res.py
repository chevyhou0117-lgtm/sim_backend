"""Simulation result layer models (res_ prefix) — engine output, read-only."""

import uuid

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# res_simulation_result
# ---------------------------------------------------------------------------
class SimulationResult(Base):
    __tablename__ = "res_simulation_result"

    result_id = Column(String(36), primary_key=True, default=_uuid)
    plan_id = Column(String(36), ForeignKey("sim_simulation_plan.plan_id"), nullable=False, unique=True)
    computation_status = Column(String(20), nullable=False)
    computation_start = Column(DateTime)
    computation_end = Column(DateTime)
    total_output = Column(Integer)
    output_per_hour = Column(Numeric(10, 3))
    overall_lbr = Column(Numeric(5, 4))
    bottleneck_equipment_id = Column(String(36))
    bottleneck_utilization = Column(Numeric(5, 4))
    material_shortage_count = Column(Integer)
    material_shortage_minutes = Column(Numeric(10, 2))
    equipment_failure_count = Column(Integer)
    equipment_downtime_minutes = Column(Numeric(10, 2))
    result_summary = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    plan = relationship("SimulationPlan", back_populates="result")
    line_balance_results = relationship("LineBalanceResult", back_populates="result")
    smt_capacity_result = relationship("SMTCapacityResult", back_populates="result", uselist=False)
    state_snapshots = relationship("SimulationStateSnapshot", back_populates="result")
    ai_analysis = relationship("AIAnalysisResult", back_populates="result", uselist=False)


# ---------------------------------------------------------------------------
# res_line_balance_result
# ---------------------------------------------------------------------------
class LineBalanceResult(Base):
    __tablename__ = "res_line_balance_result"

    lb_result_id = Column(String(36), primary_key=True, default=_uuid)
    result_id = Column(String(36), ForeignKey("res_simulation_result.result_id"), nullable=False)
    line_id = Column(String(36), ForeignKey("md_production_line.line_id"), nullable=False)
    takt_time = Column(Numeric(10, 3), nullable=False)
    lbr = Column(Numeric(5, 4), nullable=False)
    balance_loss_rate = Column(Numeric(5, 4), nullable=False)
    bottleneck_operation_id = Column(String(36))
    bottleneck_ct = Column(Numeric(10, 3))
    idle_operation_id = Column(String(36))
    operation_load_detail = Column(JSONB)
    workshop_load_rate = Column(Numeric(5, 4))
    factory_load_rate = Column(Numeric(5, 4))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    result = relationship("SimulationResult", back_populates="line_balance_results")
    production_line = relationship("ProductionLine")


# ---------------------------------------------------------------------------
# res_smt_capacity_result
# ---------------------------------------------------------------------------
class SMTCapacityResult(Base):
    __tablename__ = "res_smt_capacity_result"

    smt_result_id = Column(String(36), primary_key=True, default=_uuid)
    result_id = Column(String(36), ForeignKey("res_simulation_result.result_id"), nullable=False, unique=True)
    time_granularity = Column(String(10), nullable=False)
    placement_rate = Column(Numeric(5, 4), nullable=False)
    smt_line_count = Column(Integer, nullable=False)
    total_demand_points = Column(Numeric(20, 2))
    total_effective_capacity_points = Column(Numeric(20, 2))
    max_gap_period_label = Column(String(20))
    max_gap_lines_needed = Column(Integer)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    result = relationship("SimulationResult", back_populates="smt_capacity_result")
    period_results = relationship("SMTCapacityPeriodResult", back_populates="smt_result")


# ---------------------------------------------------------------------------
# res_smt_capacity_period_result
# ---------------------------------------------------------------------------
class SMTCapacityPeriodResult(Base):
    __tablename__ = "res_smt_capacity_period_result"

    period_result_id = Column(String(36), primary_key=True, default=_uuid)
    smt_result_id = Column(String(36), ForeignKey("res_smt_capacity_result.smt_result_id"), nullable=False)
    period_label = Column(String(20), nullable=False)
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)
    working_days = Column(Integer, nullable=False)
    demand_points = Column(Numeric(20, 2), nullable=False)
    theoretical_capacity_points = Column(Numeric(20, 2), nullable=False)
    effective_capacity_points = Column(Numeric(20, 2), nullable=False)
    gap_points = Column(Numeric(20, 2), nullable=False)
    gap_lines_needed = Column(Integer, nullable=False)
    utilization_rate = Column(Numeric(5, 4), nullable=False)
    period_detail = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    smt_result = relationship("SMTCapacityResult", back_populates="period_results")


# ---------------------------------------------------------------------------
# res_simulation_state_snapshot
# ---------------------------------------------------------------------------
class SimulationStateSnapshot(Base):
    __tablename__ = "res_simulation_state_snapshot"

    snapshot_id = Column(String(36), primary_key=True, default=_uuid)
    result_id = Column(String(36), ForeignKey("res_simulation_result.result_id"), nullable=False)
    sim_timestamp_sec = Column(Numeric(10, 3), nullable=False)
    equipment_states = Column(JSONB, nullable=False)
    wip_states = Column(JSONB)
    warehouse_states = Column(JSONB)
    agv_states = Column(JSONB)
    snapshot_interval_sec = Column(Integer, nullable=False, default=60)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    result = relationship("SimulationResult", back_populates="state_snapshots")
