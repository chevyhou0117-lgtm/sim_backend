"""Seed script: insert Main Module + Packaging stages with multiple lines each.

Run: cd sim_backend && .venv/bin/python seed.py
"""

import uuid
from datetime import date, time

from app.database import SessionLocal
from app.models.biz import ProductionTask
from app.models.md import (
    BOP,
    BOPProcess,
    Equipment,
    Factory,
    Operation,
    Product,
    ProductionLine,
    Shift,
    Stage,
    WorkCalendar,
)
from app.models.sim import SimulationPlan

db = SessionLocal()


def uid() -> str:
    return str(uuid.uuid4())


# ============================================================================
# 1. Factory
# ============================================================================
factory_id = uid()
db.add(Factory(
    factory_id=factory_id,
    factory_code="HST_P9",
    factory_name="Houston P9 Factory",
    location="Houston, TX, USA",
    timezone="America/Chicago",
    status="ACTIVE",
))

# ============================================================================
# 2. Stages — Main Module & Packaging
# ============================================================================
main_module_stage_id = uid()
packaging_stage_id = uid()

db.add(Stage(
    stage_id=main_module_stage_id,
    factory_id=factory_id,
    stage_code="MAIN_MODULE",
    stage_name="Main Module Assembly",
    sequence=1,
    stage_type="ASSEMBLY",
    status="ACTIVE",
))
db.add(Stage(
    stage_id=packaging_stage_id,
    factory_id=factory_id,
    stage_code="PACKAGING",
    stage_name="Packaging",
    sequence=2,
    stage_type="PACKAGING",
    status="ACTIVE",
))

# ============================================================================
# 3. Production Lines — 2 per stage
# ============================================================================
mm_line_01_id = uid()
mm_line_02_id = uid()
pk_line_01_id = uid()
pk_line_02_id = uid()

db.add(ProductionLine(
    line_id=mm_line_01_id,
    stage_id=main_module_stage_id,
    line_code="L_HST_MM_01",
    line_name="Main Module Line 01",
    status="ACTIVE",
    sort_order=1,
))
db.add(ProductionLine(
    line_id=mm_line_02_id,
    stage_id=main_module_stage_id,
    line_code="L_HST_MM_02",
    line_name="Main Module Line 02",
    status="ACTIVE",
    sort_order=2,
))
db.add(ProductionLine(
    line_id=pk_line_01_id,
    stage_id=packaging_stage_id,
    line_code="L_HST_PK_01",
    line_name="Packaging Line 01",
    status="ACTIVE",
    sort_order=1,
))
db.add(ProductionLine(
    line_id=pk_line_02_id,
    stage_id=packaging_stage_id,
    line_code="L_HST_PK_02",
    line_name="Packaging Line 02",
    status="ACTIVE",
    sort_order=2,
))

# ============================================================================
# 4. Product
# ============================================================================
product_id = uid()
db.add(Product(
    product_id=product_id,
    product_code="PG548",
    product_name="NVD Bianca PG548 UT3.0B",
    product_category="GPU Module",
    unit="PCS",
    status="ACTIVE",
))

# ============================================================================
# 5. Main Module Stage — Operations & Equipment
# ============================================================================
# Each tuple: (operation_name, equipment_list, actual_ct, design_ct, workers, operation_type)
MODULE_DATA = [
    ("Carrier Tray Loading", [
        ("Carrier Tray Up-Down Recovery (Feeding)", "ROBOT", "t_id_CT_HOUM548ZPRL_01_ZPRL01"),
    ], 15.0, 31.0, 0, "OTHER"),
    ("TOP Stiffener Assembly", [
        ("TOP Stiffener Assembly Machine", "ROBOT", "t_id_CT_HOUM548TS1_TS01"),
        ("Cache Machine (TOP Stiffener)", "OTHER", "t_id_CT_HOUM548TPSL_R_BF01"),
    ], 11.7, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S2", [
        ("Thermal Adhesive Applicator S2", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ01"),
    ], 15.8, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S3", [
        ("Thermal Adhesive Applicator S3", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ02"),
    ], 16.4, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S4", [
        ("Thermal Adhesive Applicator S4", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ03"),
    ], 19.2, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S5", [
        ("Thermal Adhesive Applicator S5", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ04"),
    ], 16.0, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S6", [
        ("Thermal Adhesive Applicator S6", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ05"),
    ], 14.8, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S7", [
        ("Thermal Adhesive Applicator S7", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ06"),
    ], 12.0, 31.0, 0, "OTHER"),
    ("PCBA Board Assembly", [
        ("PCBA Assembly Machine", "ROBOT", "t_id_CT_HOUM548PCB_PCB01"),
        ("Cache Machine (PCBA)", "OTHER", "t_id_CT_HOUM548TPSL_L_BF02"),
    ], 24.4, 31.0, 0, "OTHER"),
    ("PCBA Pressing", [
        ("PCBA Press Machine", "ROBOT", "t_id_CT_HOUM548YH11_YH01"),
    ], 15.0, 31.0, 0, "OTHER"),
    ("FA Maintenance Inspection 1", [
        ("Manual FA Inspection Station 1", "WORKSTATION", "t_id_CT_HOUM548HM_HM01"),
    ], 9.97, 31.0, 1, "MANUAL"),
    ("Thermal Adhesive Application S11", [
        ("Thermal Adhesive Applicator S11", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ09"),
    ], 19.3, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S12", [
        ("Thermal Adhesive Applicator S12", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ10"),
    ], 19.2, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S13", [
        ("Thermal Adhesive Applicator S13", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ11"),
    ], 18.1, 31.0, 0, "OTHER"),
    ("Thermal Adhesive Application S14", [
        ("Thermal Adhesive Applicator S14", "ROBOT", "t_id_CT_HOUM548DRJ2_DRJ12"),
    ], 15.0, 31.0, 0, "OTHER"),
    ("BOT Stiffener Assembly", [
        ("BOT Stiffener Assembly Machine", "ROBOT", "t_id_CT_HOUM548TPSL_L_BF03"),
        ("Cache Machine (BOT Stiffener)", "OTHER", "t_id_CT_HOUM548BS_BS01"),
    ], 28.5, 31.0, 0, "OTHER"),
    ("BOT Stiffener Pressing", [
        ("BOT Stiffener Press Machine", "ROBOT", "t_id_CT_HOUM548YH11_YH02"),
    ], 15.0, 31.0, 0, "OTHER"),
    ("BOT Screw Pre-Lock S17", [
        ("Screw Pre-Lock Machine S17", "ROBOT", "t_id_CT_HOUM548CNTSC12_CNTSC01"),
    ], 26.0, 31.0, 0, "OTHER"),
    ("BOT Screw Pre-Lock S18", [
        ("Screw Pre-Lock Machine S18", "ROBOT", "t_id_CT_HOUM548CNTSC12_CNTSC02"),
    ], 28.4, 31.0, 0, "OTHER"),
    ("BOT Screw Lock S19", [
        ("Screw Lock Machine S19", "ROBOT", "t_id_CT_HOUM548CNTSC12_CNTSC03"),
    ], 19.9, 31.0, 0, "OTHER"),
    ("BOT Screw Lock S20", [
        ("Screw Lock Machine S20", "ROBOT", "t_id_CT_HOUM548BSSC20_BSSC01"),
    ], 24.0, 31.0, 0, "OTHER"),
    ("BOT Screw Lock S21", [
        ("Screw Lock Machine S21", "ROBOT", "t_id_CT_HOUM548BSSC20_BSSC02"),
    ], 22.3, 31.0, 0, "OTHER"),
    ("FA Maintenance Inspection 2", [
        ("Manual FA Inspection Station 2", "WORKSTATION", "t_id_CT_HOUM548HM_HM02"),
    ], 9.97, 31.0, 1, "MANUAL"),
    ("Board Flip", [
        ("Flip-Over Machine", "ROBOT", "t_id_CT_HOUM548FM_FM01"),
    ], 17.2, 31.0, 0, "OTHER"),
    ("PCBA Screw Locking", [
        ("PCBA Screw Lock Machine", "ROBOT", "t_id_CT_HOUM548PCBSC24_PCBSC01"),
    ], 24.6, 31.0, 0, "OTHER"),
    ("Final Inspection", [
        ("Manual Final Inspection Station", "WORKSTATION", "t_id_CT_HOUM548HM_HM03"),
    ], 9.97, 31.0, 1, "MANUAL"),
    ("Automatic Sorting", [
        ("Auto Sorting Machine", "ROBOT", "t_id_CT_HOUM548SFL_SFL01"),
        ("Cache Machine (Sorting)", "OTHER", "t_id_CT_HOUM548TPSL_L_BF04"),
    ], 19.0, 31.0, 0, "OTHER"),
    ("Carrier Tray Unloading", [
        ("Carrier Tray Up-Down Recovery (Unloading)", "ROBOT", "t_id_CT_HOUM548ZPRL_02_ZPRL02"),
    ], 9.97, 31.0, 0, "OTHER"),
]

# ============================================================================
# 6. Packaging Stage — Operations & Equipment
# ============================================================================
PACK_DATA = [
    ("Inbound Loading", [
        ("Loading Tray Rack", "ROBOT", "t_id_CT_HST_Pack_Trolley_TR01"),
        ("Carrier Machine (Inbound)", "ROBOT", "t_id_CT_HOPBLSI_LD01"),
    ], 29.0, 19.0, 0, "OTHER"),
    ("Transfer to Line", [
        ("Transfer Machine 1", "OTHER", "t_id_CT_HOPBYZ_CV01"),
    ], 12.0, 10.0, 0, "OTHER"),
    ("Manual Packing A1", [
        ("Manual Packing Station A1", "WORKSTATION", "t_id_CT_HOPBHM_A_HM01"),
    ], 7.0, 6.0, 1, "MANUAL"),
    ("AOI Carrier Conveyor", [
        ("AOI Carrier Cross Conveyor", "OTHER", "t_id_TR7700L_QH_SI_AOI01"),
    ], 7.0, 20.0, 0, "OTHER"),
    ("Manual Packing A2", [
        ("Manual Packing Station A2", "WORKSTATION", "t_id_CT_HOPBHM_A_HM02"),
    ], 7.0, 6.0, 1, "MANUAL"),
    ("Cross Transfer", [
        ("Transfer Machine 2", "OTHER", "t_id_CT_HOPBCRO_CV02"),
    ], 12.0, 10.0, 0, "OTHER"),
    ("Manual Packing B1", [
        ("Manual Packing Station B1", "WORKSTATION", "t_id_CT_HOPBHM_B_HM03"),
    ], 24.0, 6.0, 0, "MANUAL"),
    ("Manual Packing B2", [
        ("Manual Packing Station B2", "WORKSTATION", "t_id_CT_HOPBHM_B_HM04"),
    ], 15.0, 10.0, 1, "MANUAL"),
    ("Auto AOI Inspection", [
        ("Auto AOI Inspection Machine", "AOI", "t_id_CT_HOPBAOI_AOI02"),
    ], 45.5, 40.0, 0, "AOI"),
    ("Manual Packing C1", [
        ("Manual Packing Station C1", "WORKSTATION", "t_id_CT_HOPBHM_C_HM05"),
    ], 7.0, 10.0, 1, "MANUAL"),
    ("Manual Packing C2", [
        ("Manual Packing Station C2", "WORKSTATION", "t_id_CT_HOPBHM_C_HM06"),
    ], 7.0, 10.0, 1, "MANUAL"),
    ("Edge Folding and Sealing", [
        ("Auto Edge Folding Sealer", "ROBOT", "t_id_CT_HOPBFWX1_X01"),
    ], 6.0, 6.0, 0, "OTHER"),
    ("Corner Turning", [
        ("Corner Turner", "OTHER", "t_id_CT_HOPBWST_W01"),
    ], 7.0, 6.0, 0, "OTHER"),
    ("Top Corner Sealing", [
        ("Auto Top Corner Sealer", "ROBOT", "t_id_CT_HOPBFWX2_X02"),
    ], 6.0, 3.3, 0, "OTHER"),
    ("Seal Label Application", [
        ("Auto Seal Label Applicator", "ROBOT", "t_id_CT_HOPBFKB_LB01"),
    ], 6.8, 5.0, 0, "OTHER"),
    ("Palletizing", [
        ("Auto Palletizer", "ROBOT", "t_id_CT_HOPBMD_MD01"),
    ], 45.0, 17.0, 0, "OTHER"),
    ("Outbound Transfer", [
        ("Transfer Machine 3", "OTHER", "t_id_CT_HOPBYZ_CV03"),
    ], 9.98, 5.0, 0, "OTHER"),
    ("Outbound Unloading", [
        ("Carrier Machine (Outbound)", "ROBOT", "t_id_CT_HOPBLSJ_LD02"),
        ("Unloading Tray Rack", "ROBOT", "t_id_CT_HST_Pack_Trolley_TR02"),
    ], 22.5, 9.0, 0, "OTHER"),
]

PACK_PANEL_QTY = [1] * 13 + [2] * 5


# ============================================================================
# Helpers
# ============================================================================
def insert_stage_operations(stage_id: str, code_prefix: str, data: list):
    """Insert operations and their equipment under a stage.

    Returns: [(op_id, actual_ct, workers), ...] preserving input order.
    """
    results = []
    for seq, (op_name, eq_list, actual_ct, design_ct, workers, op_type) in enumerate(data, 1):
        op_id = uid()
        op_code = f"{code_prefix}_OP{seq:03d}"

        db.add(Operation(
            operation_id=op_id,
            stage_id=stage_id,
            operation_code=op_code,
            operation_name=op_name,
            sequence=seq,
            operation_type=op_type,
            is_key_operation=False,
            status="ACTIVE",
        ))

        for eq_idx, (eq_name, eq_type, prim_path) in enumerate(eq_list):
            eq_code = f"{code_prefix}_EQ{seq:03d}_{eq_idx + 1:02d}"
            db.add(Equipment(
                equipment_id=uid(),
                operation_id=op_id,
                equipment_code=eq_code,
                equipment_name=eq_name,
                equipment_type=eq_type,
                standard_ct=design_ct,
                status="ACTIVE",
                sort_order=eq_idx + 1,
                creator_binding_id=prim_path,
            ))

        results.append((op_id, actual_ct, workers))
    return results


def insert_bop_for_line(
    line_id: str,
    version: str,
    operations: list,
    panel_qtys: list[int] | None = None,
):
    """Create a BOP for a production line referencing the given stage operations."""
    bop_id = uid()
    db.add(BOP(
        bop_id=bop_id,
        product_id=product_id,
        line_id=line_id,
        bop_version=version,
        is_active=True,
        created_by="seed_script",
    ))

    for idx, (op_id, actual_ct, workers) in enumerate(operations):
        seq = idx + 1
        panel_qty = panel_qtys[idx] if panel_qtys else 1

        db.add(BOPProcess(
            bop_process_id=uid(),
            bop_id=bop_id,
            operation_id=op_id,
            sequence=seq,
            standard_ct=actual_ct,
            panel_qty=panel_qty if panel_qty > 1 else None,
            ct_per_panel=actual_ct * panel_qty if panel_qty > 1 else None,
            yield_rate=1.0,
            standard_worker_count=workers,
        ))


# ============================================================================
# 7. Insert Operations per stage (shared across lines in that stage)
# ============================================================================
mm_ops = insert_stage_operations(main_module_stage_id, "MM", MODULE_DATA)
pk_ops = insert_stage_operations(packaging_stage_id, "PK", PACK_DATA)

# ============================================================================
# 8. BOP per line — each line gets its own BOP, different lines can diverge later
# ============================================================================
insert_bop_for_line(mm_line_01_id, "v1.0", mm_ops)
insert_bop_for_line(mm_line_02_id, "v1.0", mm_ops)
insert_bop_for_line(pk_line_01_id, "v1.0", pk_ops, PACK_PANEL_QTY)
insert_bop_for_line(pk_line_02_id, "v1.0", pk_ops, PACK_PANEL_QTY)

# Update line operation counts
db.query(ProductionLine).filter(
    ProductionLine.line_id.in_([mm_line_01_id, mm_line_02_id])
).update({"operation_count": len(MODULE_DATA)}, synchronize_session=False)
db.query(ProductionLine).filter(
    ProductionLine.line_id.in_([pk_line_01_id, pk_line_02_id])
).update({"operation_count": len(PACK_DATA)}, synchronize_session=False)

# Update stage line_count
db.query(Stage).filter(Stage.stage_id == main_module_stage_id).update({"line_count": 2})
db.query(Stage).filter(Stage.stage_id == packaging_stage_id).update({"line_count": 2})

# ============================================================================
# 9. Work Calendar + Shift
# ============================================================================
cal_id = uid()
db.add(WorkCalendar(
    calendar_id=cal_id,
    factory_id=factory_id,
    calendar_date=date(2026, 4, 15),
    is_working_day=True,
    day_type="WEEKDAY",
    total_work_hours=11.0,
))
db.add(Shift(
    shift_id=uid(),
    calendar_id=cal_id,
    shift_name="Day Shift",
    start_time=time(8, 0),
    end_time=time(20, 0),
    work_hours=11.0,
    break_minutes=60,
    shift_order=1,
))

# ============================================================================
# 10. Simulation Plan + Production Tasks (one per line)
# ============================================================================
plan_id = uid()
db.add(SimulationPlan(
    plan_id=plan_id,
    plan_name="Main Module + Packaging Baseline Evaluation",
    plan_description="Baseline simulation across 2 module lines and 2 packaging lines with standard CT",
    factory_id=factory_id,
    status="DRAFT",
    enabled_simulators=["PRODUCTION", "LINE_BALANCE"],
    simulation_duration_hours=11.0,
    created_by="seed_script",
))

line_bindings = [
    (mm_line_01_id, main_module_stage_id, 1),
    (mm_line_02_id, main_module_stage_id, 2),
    (pk_line_01_id, packaging_stage_id, 3),
    (pk_line_02_id, packaging_stage_id, 4),
]
for line_id, stage_id, sequence in line_bindings:
    db.add(ProductionTask(
        task_id=uid(),
        plan_id=plan_id,
        stage_id=stage_id,
        line_id=line_id,
        product_code="PG548",
        plan_quantity=500,
        production_sequence=sequence,
        data_source="MANUAL_IMPORT",
    ))

# ============================================================================
# Commit
# ============================================================================
db.commit()

# Print summary
mm_ops_count = db.query(Operation).filter(Operation.stage_id == main_module_stage_id).count()
pk_ops_count = db.query(Operation).filter(Operation.stage_id == packaging_stage_id).count()
mm_eq_count = db.query(Equipment).join(Operation).filter(
    Operation.stage_id == main_module_stage_id
).count()
pk_eq_count = db.query(Equipment).join(Operation).filter(
    Operation.stage_id == packaging_stage_id
).count()
bop_count = db.query(BOP).count()

print("Seed complete:")
print("  Factory:     1 (Houston P9)")
print("  Stages:      2 (Main Module, Packaging)")
print("  Lines:       4 (MM-01, MM-02, PK-01, PK-02)")
print(f"  Main Module: {mm_ops_count} operations, {mm_eq_count} equipment")
print(f"  Packaging:   {pk_ops_count} operations, {pk_eq_count} equipment")
print("  Product:     1 (PG548)")
print(f"  BOPs:        {bop_count} (one per line)")
print("  Calendar:    1 day, 1 shift (11h)")
print("  Plan:        1 (DRAFT, 500 pcs per line × 4 lines)")
print(f"  Plan ID:     {plan_id}")

db.close()
