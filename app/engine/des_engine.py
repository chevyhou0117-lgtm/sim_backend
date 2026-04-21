"""Discrete Event Simulation (DES) engine using SimPy.

Simulates product flow through BOP processes on a production line.
Produces millisecond-precision events for 3D visualization in Omniverse.

Each Operation is modeled as a simpy.Resource with capacity = equipment count.
Products flow through processes sequentially, queuing when resources are busy.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import simpy
from sqlalchemy.orm import Session

from app.engine.common import (
    ResolvedProcess,
    SimEvent,
    get_enabled_constraints,
    load_resolved_processes,
)
from app.models.biz import ProductionTask
from app.models.md import (
    BOP,
    BOPProcess,
    EquipmentFailureParam,
    OperationTransition,
    ProductionLine,
    Stage,
    WIPBuffer,
)
from app.models.res import SimulationResult, SimulationStateSnapshot
from app.models.sim import AnomalyInjection, SimulationPlan

# Default changeover time inserted between consecutive tasks of different
# product_code on the same line. Will be replaced by per-line configured
# changeover data once that table is modeled.
DEFAULT_CHANGEOVER_SEC = 300  # 5 minutes


@dataclass
class DESMetrics:
    """Collected metrics during simulation."""

    total_output: int = 0
    ng_count: int = 0
    events: list[SimEvent] = field(default_factory=list)
    equipment_busy_time: dict[str, float] = field(default_factory=dict)  # eq_id -> seconds busy
    equipment_idle_time: dict[str, float] = field(default_factory=dict)
    material_shortage_count: int = 0
    equipment_failure_count: int = 0
    equipment_downtime_seconds: float = 0.0
    hourly_output: list[dict] = field(default_factory=list)  # [{hour, actual, plan, defect}]


class ProductionLineSimulation:
    """SimPy-based simulation for a single production line."""

    def __init__(
        self,
        env: simpy.Environment,
        processes: list[ResolvedProcess],
        transitions: dict[tuple[str, str], tuple[float, float]],
        constraints: set[str],
        failure_params: dict[str, tuple[float, float]],  # eq_id -> (mtbf_sec, mttr_sec)
        anomalies: list[AnomalyInjection],
        wip_buffers: dict[str, int],  # between operation pairs -> capacity
        upstream_store: simpy.Store | None = None,
        downstream_store: simpy.Store | None = None,
        inbound_delay_sec: float = 0.0,
    ):
        self.env = env
        self.processes = processes
        self.transitions = transitions
        self.constraints = constraints
        self.anomalies = anomalies
        self.metrics = DESMetrics()
        self.upstream_store = upstream_store
        self.downstream_store = downstream_store
        self.inbound_delay_sec = inbound_delay_sec

        # Create resources for each process (capacity = equipment count)
        self.resources: dict[str, simpy.Resource] = {}
        for proc in processes:
            self.resources[proc.operation_id] = simpy.Resource(env, capacity=proc.equipment_count)

        # WIP buffers (only if WIP_CAPACITY constraint enabled)
        self.wip_containers: dict[str, simpy.Container] = {}
        if "WIP_CAPACITY" in constraints:
            for key, cap in wip_buffers.items():
                self.wip_containers[key] = simpy.Container(env, capacity=cap, init=0)

        # Track which equipment is handling each request (for prim path mapping)
        self._eq_assignment: dict[str, int] = {}  # operation_id -> current equipment index

        # Equipment failure processes
        if "EQUIPMENT_FAILURE" in constraints:
            for proc in processes:
                for eq_id in proc.equipment_ids:
                    if eq_id in failure_params:
                        mtbf_sec, mttr_sec = failure_params[eq_id]
                        env.process(self._equipment_failure(proc, eq_id, mtbf_sec, mttr_sec))

        # Anomaly injection processes
        for anomaly in anomalies:
            if anomaly.anomaly_type == "EQUIPMENT_DOWNTIME":
                env.process(self._anomaly_downtime(anomaly))

    def _record_event(self, equipment_id: str, prim_path: str | None, event_type: str,
                      product_id: str | None = None, metadata: dict | None = None):
        """Record a simulation event with millisecond timestamp."""
        self.metrics.events.append(SimEvent(
            timestamp_ms=int(self.env.now * 1000),
            equipment_id=equipment_id,
            prim_path=prim_path,
            event_type=event_type,
            product_id=product_id,
            metadata=metadata,
        ))

    def _get_equipment_for_process(self, proc: ResolvedProcess) -> tuple[str, str | None]:
        """Round-robin equipment assignment for a process."""
        idx = self._eq_assignment.get(proc.operation_id, 0)
        eq_id = proc.equipment_ids[idx % len(proc.equipment_ids)] if proc.equipment_ids else proc.operation_id
        prim = proc.equipment_prim_paths[idx % len(proc.equipment_prim_paths)] if proc.equipment_prim_paths else None
        self._eq_assignment[proc.operation_id] = idx + 1
        return eq_id, prim

    def product_flow(self, product_id: str):
        """Generator: one product unit flows through all BOP processes."""
        for i, proc in enumerate(self.processes):
            resource = self.resources[proc.operation_id]
            eq_id, prim_path = self._get_equipment_for_process(proc)

            # Request the resource (queue if busy)
            with resource.request() as req:
                yield req

                # Record processing start
                self._record_event(eq_id, prim_path, "PROCESSING_START", product_id,
                                   {"ct": proc.effective_ct, "sequence": proc.sequence})

                start = self.env.now
                yield self.env.timeout(proc.effective_ct)

                # Track busy time
                self.metrics.equipment_busy_time[eq_id] = (
                    self.metrics.equipment_busy_time.get(eq_id, 0) + proc.effective_ct
                )

                # Record processing end
                self._record_event(eq_id, prim_path, "PROCESSING_END", product_id)

            # Yield rate check
            if random.random() > proc.yield_rate:
                self.metrics.ng_count += 1
                self._record_event(eq_id, prim_path, "NG_DETECTED", product_id)
                return  # Product scrapped, don't continue

            # Handle transition to next process
            if i < len(self.processes) - 1:
                next_proc = self.processes[i + 1]
                key = (proc.operation_id, next_proc.operation_id)
                if key in self.transitions:
                    transfer_time, wait_time = self.transitions[key]
                    if transfer_time > 0 or wait_time > 0:
                        yield self.env.timeout(transfer_time + wait_time)

        # Product finished this line's BOP — either hand off to next stage, or complete
        last_eq = self.processes[-1].equipment_ids[0] if self.processes[-1].equipment_ids else "output"
        if self.downstream_store is not None:
            self._record_event(last_eq, None, "STAGE_HANDOFF", product_id)
            yield self.downstream_store.put(product_id)
        else:
            self.metrics.total_output += 1
            self._record_event(last_eq, None, "PRODUCT_COMPLETE", product_id)

    def task_queue_runner(
        self,
        tasks: list[ProductionTask],
        changeover_sec: float = DEFAULT_CHANGEOVER_SEC,
    ):
        """Run tasks on this line **sequentially** in production_sequence order.

        Between two consecutive tasks with different product_code, insert a
        changeover timeout during which no new products are fed. Products from
        the current task still finish flowing through downstream operations
        before the next task starts feeding.
        """
        prev_product_code: str | None = None
        first_eq = (
            self.processes[0].equipment_ids[0]
            if self.processes and self.processes[0].equipment_ids
            else "line"
        )

        for task in tasks:
            qty = (task.plan_quantity or 0) - (task.completed_qty or 0)
            if qty <= 0:
                continue

            # Changeover if product_code changed
            if (
                prev_product_code is not None
                and prev_product_code != task.product_code
                and changeover_sec > 0
            ):
                self._record_event(
                    first_eq, None, "CHANGEOVER_START", None,
                    {
                        "from_product": prev_product_code,
                        "to_product": task.product_code,
                        "duration_sec": changeover_sec,
                    },
                )
                yield self.env.timeout(changeover_sec)
                self._record_event(
                    first_eq, None, "CHANGEOVER_END", None,
                    {
                        "from_product": prev_product_code,
                        "to_product": task.product_code,
                    },
                )

            # Feed all products of this task with a tiny stagger, then wait
            # for all of them to finish (or scrap) before the next task feeds.
            product_procs: list[simpy.Process] = []
            for i in range(qty):
                product_id = f"{task.task_id}_unit_{i:05d}"
                product_procs.append(self.env.process(self.product_flow(product_id)))
                yield self.env.timeout(0.001)

            if product_procs:
                yield self.env.all_of(product_procs)

            prev_product_code = task.product_code

    def stage_consumer(self):
        """Daemon for non-entry stages: pull products from upstream stage store,
        apply inter-stage transfer delay, then spawn product_flow through this line's BOP."""
        while True:
            product_id = yield self.upstream_store.get()
            if self.inbound_delay_sec > 0:
                yield self.env.timeout(self.inbound_delay_sec)
            self.env.process(self.product_flow(product_id))

    def _equipment_failure(self, proc: ResolvedProcess, eq_id: str,
                           mtbf_sec: float, mttr_sec: float):
        """Random equipment failure based on MTBF/MTTR."""
        prim_path = None
        for j, eid in enumerate(proc.equipment_ids):
            if eid == eq_id:
                prim_path = proc.equipment_prim_paths[j] if j < len(proc.equipment_prim_paths) else None
                break

        while True:
            # Wait for failure
            time_to_failure = random.expovariate(1.0 / mtbf_sec)
            yield self.env.timeout(time_to_failure)

            # Seize the resource (simulate breakdown)
            resource = self.resources[proc.operation_id]
            with resource.request(priority=-1) as req:
                yield req
                self._record_event(eq_id, prim_path, "FAILURE_START")
                self.metrics.equipment_failure_count += 1

                # Repair time
                repair_time = random.expovariate(1.0 / mttr_sec)
                yield self.env.timeout(repair_time)
                self.metrics.equipment_downtime_seconds += repair_time

                self._record_event(eq_id, prim_path, "FAILURE_END")

    def _anomaly_downtime(self, anomaly: AnomalyInjection):
        """Forced equipment downtime from anomaly injection."""
        start_sec = float(anomaly.start_sim_hour) * 3600
        duration_sec = float(anomaly.duration_minutes) * 60

        yield self.env.timeout(start_sec)

        # Find the process that owns this equipment
        target_proc = None
        for proc in self.processes:
            if anomaly.target_id in proc.equipment_ids:
                target_proc = proc
                break

        if not target_proc:
            return

        resource = self.resources[target_proc.operation_id]
        with resource.request(priority=-1) as req:
            yield req
            prim_path = None
            for j, eid in enumerate(target_proc.equipment_ids):
                if eid == anomaly.target_id:
                    prim_path = target_proc.equipment_prim_paths[j] if j < len(target_proc.equipment_prim_paths) else None
                    break
            self._record_event(anomaly.target_id, prim_path, "FAILURE_START", metadata={"anomaly": True})
            yield self.env.timeout(duration_sec)
            self._record_event(anomaly.target_id, prim_path, "FAILURE_END", metadata={"anomaly": True})


def _lookup_cross_stage_transition(
    db: Session,
    upstream_stage_id: str | None,
    current_line_id: str,
) -> float:
    """Return transfer_time + mandatory_wait_time for upstream BoP's last op →
    current BoP's first op, using existing OperationTransition rows. 0 if none."""
    if upstream_stage_id is None:
        return 0.0

    current_bop = (
        db.query(BOP)
        .filter(BOP.line_id == current_line_id, BOP.is_active == True)  # noqa: E712
        .first()
    )
    if not current_bop:
        return 0.0
    first_proc = (
        db.query(BOPProcess)
        .filter(BOPProcess.bop_id == current_bop.bop_id)
        .order_by(BOPProcess.sequence.asc())
        .first()
    )
    if not first_proc:
        return 0.0

    upstream_lines = (
        db.query(ProductionLine.line_id)
        .filter(ProductionLine.stage_id == upstream_stage_id, ProductionLine.status == "ACTIVE")
        .all()
    )
    for (up_line_id,) in upstream_lines:
        up_bop = (
            db.query(BOP)
            .filter(BOP.line_id == up_line_id, BOP.is_active == True)  # noqa: E712
            .first()
        )
        if not up_bop:
            continue
        last_proc = (
            db.query(BOPProcess)
            .filter(BOPProcess.bop_id == up_bop.bop_id)
            .order_by(BOPProcess.sequence.desc())
            .first()
        )
        if not last_proc:
            continue
        tr = (
            db.query(OperationTransition)
            .filter(
                OperationTransition.from_operation_id == last_proc.operation_id,
                OperationTransition.to_operation_id == first_proc.operation_id,
            )
            .first()
        )
        if tr:
            return float(tr.transfer_time) + float(tr.mandatory_wait_time)
    return 0.0


def run_des(db: Session, plan_id: str) -> DESMetrics:
    """Execute DES simulation for all production lines in the plan.

    Returns aggregated DESMetrics with millisecond-precision events.
    """
    plan = db.query(SimulationPlan).get(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    result = db.query(SimulationResult).filter(SimulationResult.plan_id == plan_id).first()
    if not result:
        raise ValueError(f"No SimulationResult found for plan {plan_id}")

    duration_seconds = float(plan.simulation_duration_hours) * 3600
    constraints = get_enabled_constraints(db, plan_id)

    # Get all production tasks grouped by line
    tasks = (
        db.query(ProductionTask)
        .filter(ProductionTask.plan_id == plan_id)
        .order_by(ProductionTask.production_sequence)
        .all()
    )

    tasks_by_line: dict[str, list[ProductionTask]] = {}
    for t in tasks:
        tasks_by_line.setdefault(t.line_id, []).append(t)

    # Load anomalies
    anomalies = db.query(AnomalyInjection).filter(AnomalyInjection.plan_id == plan_id).all()

    all_metrics = DESMetrics()

    # Build stage topology from participating lines
    line_stage_rows = (
        db.query(ProductionLine.line_id, Stage.stage_id, Stage.sequence)
        .join(Stage, Stage.stage_id == ProductionLine.stage_id)
        .filter(ProductionLine.line_id.in_(list(tasks_by_line.keys())))
        .all()
        if tasks_by_line
        else []
    )
    line_to_stage: dict[str, str] = {lid: sid for lid, sid, _ in line_stage_rows}
    stage_seq_map: dict[str, int] = {sid: seq for _, sid, seq in line_stage_rows}
    stage_ids_in_order = sorted(stage_seq_map.keys(), key=lambda sid: stage_seq_map[sid])
    entry_stage_id = stage_ids_in_order[0] if stage_ids_in_order else None

    # One env shared across the whole plan; inter-stage Stores for product handoff
    env = simpy.Environment()
    stage_stores: dict[tuple[str, str], simpy.Store] = {}
    for i in range(len(stage_ids_in_order) - 1):
        up, down = stage_ids_in_order[i], stage_ids_in_order[i + 1]
        stage_stores[(up, down)] = simpy.Store(env)

    sims: list[ProductionLineSimulation] = []

    for line_id, line_tasks in tasks_by_line.items():
        processes = load_resolved_processes(db, plan_id, line_id)
        if not processes:
            continue

        # Load transitions
        bop = db.query(BOP).filter(BOP.line_id == line_id, BOP.is_active == True).first()  # noqa: E712
        transitions: dict[tuple[str, str], tuple[float, float]] = {}
        if bop:
            trans_rows = (
                db.query(OperationTransition)
                .filter(OperationTransition.bop_id == bop.bop_id)
                .all()
            )
            for tr in trans_rows:
                transitions[(tr.from_operation_id, tr.to_operation_id)] = (
                    float(tr.transfer_time),
                    float(tr.mandatory_wait_time),
                )

        # Load failure params
        failure_params: dict[str, tuple[float, float]] = {}
        if "EQUIPMENT_FAILURE" in constraints:
            for proc in processes:
                for eq_id in proc.equipment_ids:
                    fp = db.query(EquipmentFailureParam).filter(
                        EquipmentFailureParam.equipment_id == eq_id
                    ).first()
                    if fp:
                        failure_params[eq_id] = (
                            float(fp.mtbf_hours) * 3600,
                            float(fp.mttr_minutes) * 60,
                        )

        # Load WIP buffers
        wip_buffers: dict[str, int] = {}
        if "WIP_CAPACITY" in constraints:
            wip_rows = db.query(WIPBuffer).filter(WIPBuffer.line_id == line_id).all()
            for w in wip_rows:
                if w.pre_operation_id and w.post_operation_id:
                    key = f"{w.pre_operation_id}_{w.post_operation_id}"
                    wip_buffers[key] = w.capacity_qty or 999

        # Line-specific anomalies
        line_equipment_ids = set()
        for proc in processes:
            line_equipment_ids.update(proc.equipment_ids)
        line_anomalies = [a for a in anomalies if a.target_id in line_equipment_ids]

        # Resolve this line's stage position and attach upstream/downstream stores
        stage_id = line_to_stage.get(line_id)
        upstream_store: simpy.Store | None = None
        downstream_store: simpy.Store | None = None
        inbound_delay = 0.0
        if stage_id is not None:
            idx = stage_ids_in_order.index(stage_id)
            if idx > 0:
                upstream_store = stage_stores[(stage_ids_in_order[idx - 1], stage_id)]
                inbound_delay = _lookup_cross_stage_transition(
                    db,
                    upstream_stage_id=stage_ids_in_order[idx - 1],
                    current_line_id=line_id,
                )
            if idx < len(stage_ids_in_order) - 1:
                downstream_store = stage_stores[(stage_id, stage_ids_in_order[idx + 1])]

        sim = ProductionLineSimulation(
            env=env,
            processes=processes,
            transitions=transitions,
            constraints=constraints,
            failure_params=failure_params,
            anomalies=line_anomalies,
            wip_buffers=wip_buffers,
            upstream_store=upstream_store,
            downstream_store=downstream_store,
            inbound_delay_sec=inbound_delay,
        )
        sims.append(sim)

        # Entry-stage lines feed from their own task queue; downstream lines consume from upstream store
        if stage_id == entry_stage_id:
            env.process(sim.task_queue_runner(line_tasks))
        else:
            env.process(sim.stage_consumer())

    # Run the whole-plant simulation once
    env.run(until=duration_seconds)

    # Aggregate metrics across all lines
    for sim in sims:
        all_metrics.total_output += sim.metrics.total_output
        all_metrics.ng_count += sim.metrics.ng_count
        all_metrics.events.extend(sim.metrics.events)
        all_metrics.equipment_failure_count += sim.metrics.equipment_failure_count
        all_metrics.equipment_downtime_seconds += sim.metrics.equipment_downtime_seconds
        for eq_id, busy in sim.metrics.equipment_busy_time.items():
            all_metrics.equipment_busy_time[eq_id] = (
                all_metrics.equipment_busy_time.get(eq_id, 0) + busy
            )

    # Sort events by timestamp
    all_metrics.events.sort(key=lambda e: e.timestamp_ms)

    # Write summary to result
    hours = float(plan.simulation_duration_hours)
    result.total_output = all_metrics.total_output
    result.output_per_hour = round(all_metrics.total_output / hours, 3) if hours > 0 else 0
    result.equipment_failure_count = all_metrics.equipment_failure_count
    result.equipment_downtime_minutes = round(all_metrics.equipment_downtime_seconds / 60, 2)

    # Find bottleneck equipment (most busy)
    if all_metrics.equipment_busy_time:
        bottleneck_eq = max(all_metrics.equipment_busy_time, key=all_metrics.equipment_busy_time.get)
        result.bottleneck_equipment_id = bottleneck_eq
        result.bottleneck_utilization = round(
            all_metrics.equipment_busy_time[bottleneck_eq] / (duration_seconds), 4
        )

    # Aggregate PRODUCT_COMPLETE and NG_DETECTED into hourly buckets for chart
    hour_buckets: dict[int, dict[str, int]] = {}
    for ev in all_metrics.events:
        if ev.event_type not in ("PRODUCT_COMPLETE", "NG_DETECTED"):
            continue
        hr = int(ev.timestamp_ms // 3_600_000)
        bucket = hour_buckets.setdefault(hr, {"actual": 0, "defect": 0})
        if ev.event_type == "PRODUCT_COMPLETE":
            bucket["actual"] += 1
        else:
            bucket["defect"] += 1
    total_plan_qty = sum((t.plan_quantity or 0) for line_tasks in tasks_by_line.values() for t in line_tasks)
    plan_per_hour = round(total_plan_qty / hours) if hours > 0 else 0
    all_metrics.hourly_output = [
        {
            "hour": h,
            "actual": hour_buckets.get(h, {}).get("actual", 0),
            "defect": hour_buckets.get(h, {}).get("defect", 0),
            "plan": plan_per_hour,
        }
        for h in range(int(hours))
    ]

    # Write periodic snapshots (every 60 sim-seconds for chart data)
    snapshot_interval = 60  # seconds
    current_equipment_states: dict[str, str] = {}
    for sim in sims:
        for proc in sim.processes:
            for eq_id in proc.equipment_ids:
                current_equipment_states[eq_id] = "IDLE"

    event_idx = 0
    for t_sec in range(0, int(duration_seconds), snapshot_interval):
        # Advance events to this time
        t_ms = t_sec * 1000
        while event_idx < len(all_metrics.events) and all_metrics.events[event_idx].timestamp_ms <= t_ms:
            ev = all_metrics.events[event_idx]
            if ev.event_type == "PROCESSING_START":
                current_equipment_states[ev.equipment_id] = "BUSY"
            elif ev.event_type in ("PROCESSING_END", "PRODUCT_COMPLETE"):
                current_equipment_states[ev.equipment_id] = "IDLE"
            elif ev.event_type == "FAILURE_START":
                current_equipment_states[ev.equipment_id] = "FAILURE"
            elif ev.event_type == "FAILURE_END":
                current_equipment_states[ev.equipment_id] = "IDLE"
            event_idx += 1

        snapshot = SimulationStateSnapshot(
            snapshot_id=str(uuid.uuid4()),
            result_id=result.result_id,
            sim_timestamp_sec=round(t_sec, 3),
            equipment_states={eq: {"status": st} for eq, st in current_equipment_states.items()},
            snapshot_interval_sec=snapshot_interval,
        )
        db.add(snapshot)

    db.commit()
    return all_metrics
