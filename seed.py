"""Seed script: insert Module主线 + 自动包装线 data into database.

Run: cd sim_backend && .venv/bin/python seed.py
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import text

from app.database import SessionLocal, engine
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
from app.models.biz import ProductionTask
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
# 2. Stage
# ============================================================================
stage_id = uid()
db.add(Stage(
    stage_id=stage_id,
    factory_id=factory_id,
    stage_code="BACK_END",
    stage_name="Back-End Assembly and Packaging",
    sequence=1,
    stage_type="OTHER",
    status="ACTIVE",
))

# ============================================================================
# 3. Production Lines
# ============================================================================
module_line_id = uid()
pack_line_id = uid()

db.add(ProductionLine(
    line_id=module_line_id,
    stage_id=stage_id,
    line_code="L_HST_MODULE",
    line_name="Module Automatic Assembly Line",
    status="ACTIVE",
    sort_order=1,
    creator_binding_id=None,
))
db.add(ProductionLine(
    line_id=pack_line_id,
    stage_id=stage_id,
    line_code="L_HST_PACK",
    line_name="Automatic Packaging Line",
    status="ACTIVE",
    sort_order=2,
    creator_binding_id=None,
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
# 5. Module主线 — Operations & Equipment
# ============================================================================
# Each tuple: (operation_name, equipment_list, actual_ct, design_ct, workers, operation_type)
# equipment_list: [(eq_name, eq_type, prim_path), ...]

MODULE_DATA = [
    # Op1: Carrier Tray Loading
    ("Carrier Tray Loading", [
        ("Carrier Tray Up-Down Recovery (Feeding)", "ROBOT", "t_id_CT_HOUM548ZPRL_01_ZPRL01"),
    ], 15.0, 31.0, 0, "OTHER"),

    # Op2: TOP Stiffener Assembly (Station 1 + Cache)
    ("TOP Stiffener Assembly", [
        ("TOP Stiffener Assembly Machine", "ROBOT", "t_id_CT_HOUM548TS1_TS01"),
        ("Cache Machine (TOP Stiffener)", "OTHER", "t_id_CT_HOUM548TPSL_R_BF01"),
    ], 11.7, 31.0, 0, "OTHER"),

    # Op3-8: Thermal Adhesive S2-S7
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

    # Op9: PCBA Assembly (Station 8 + Cache)
    ("PCBA Board Assembly", [
        ("PCBA Assembly Machine", "ROBOT", "t_id_CT_HOUM548PCB_PCB01"),
        ("Cache Machine (PCBA)", "OTHER", "t_id_CT_HOUM548TPSL_L_BF02"),
    ], 24.4, 31.0, 0, "OTHER"),

    # Op10: PCBA Pressing
    ("PCBA Pressing", [
        ("PCBA Press Machine", "ROBOT", "t_id_CT_HOUM548YH11_YH01"),
    ], 15.0, 31.0, 0, "OTHER"),

    # Op11: FA Inspection 1
    ("FA Maintenance Inspection 1", [
        ("Manual FA Inspection Station 1", "WORKSTATION", "t_id_CT_HOUM548HM_HM01"),
    ], 9.97, 31.0, 1, "MANUAL"),

    # Op12-15: Thermal Adhesive S11-S14
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

    # Op16: BOT Stiffener Assembly (Station 15 + Cache) — BOTTLENECK
    ("BOT Stiffener Assembly", [
        ("BOT Stiffener Assembly Machine", "ROBOT", "t_id_CT_HOUM548TPSL_L_BF03"),
        ("Cache Machine (BOT Stiffener)", "OTHER", "t_id_CT_HOUM548BS_BS01"),
    ], 28.5, 31.0, 0, "OTHER"),

    # Op17: BOT Stiffener Pressing
    ("BOT Stiffener Pressing", [
        ("BOT Stiffener Press Machine", "ROBOT", "t_id_CT_HOUM548YH11_YH02"),
    ], 15.0, 31.0, 0, "OTHER"),

    # Op18-22: Screw locking S17-S21
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

    # Op23: FA Inspection 2
    ("FA Maintenance Inspection 2", [
        ("Manual FA Inspection Station 2", "WORKSTATION", "t_id_CT_HOUM548HM_HM02"),
    ], 9.97, 31.0, 1, "MANUAL"),

    # Op24: Board Flip
    ("Board Flip", [
        ("Flip-Over Machine", "ROBOT", "t_id_CT_HOUM548FM_FM01"),
    ], 17.2, 31.0, 0, "OTHER"),

    # Op25: PCBA Screw Lock
    ("PCBA Screw Locking", [
        ("PCBA Screw Lock Machine", "ROBOT", "t_id_CT_HOUM548PCBSC24_PCBSC01"),
    ], 24.6, 31.0, 0, "OTHER"),

    # Op26: Final Inspection
    ("Final Inspection", [
        ("Manual Final Inspection Station", "WORKSTATION", "t_id_CT_HOUM548HM_HM03"),
    ], 9.97, 31.0, 1, "MANUAL"),

    # Op27: Auto Sorting (Station 26 + Cache)
    ("Automatic Sorting", [
        ("Auto Sorting Machine", "ROBOT", "t_id_CT_HOUM548SFL_SFL01"),
        ("Cache Machine (Sorting)", "OTHER", "t_id_CT_HOUM548TPSL_L_BF04"),
    ], 19.0, 31.0, 0, "OTHER"),

    # Op28: Carrier Tray Unloading
    ("Carrier Tray Unloading", [
        ("Carrier Tray Up-Down Recovery (Unloading)", "ROBOT", "t_id_CT_HOUM548ZPRL_02_ZPRL02"),
    ], 9.97, 31.0, 0, "OTHER"),
]

# ============================================================================
# 6. 自动包装线 — Operations & Equipment
# ============================================================================
PACK_DATA = [
    # Op1: Inbound Loading (11-1) — 2 equipment
    ("Inbound Loading", [
        ("Loading Tray Rack", "ROBOT", "t_id_CT_HST_Pack_Trolley_TR01"),
        ("Carrier Machine (Inbound)", "ROBOT", "t_id_CT_HOPBLSI_LD01"),
    ], 29.0, 19.0, 0, "OTHER"),

    # Op2: Transfer 1 (11-2)
    ("Transfer to Line", [
        ("Transfer Machine 1", "OTHER", "t_id_CT_HOPBYZ_CV01"),
    ], 12.0, 10.0, 0, "OTHER"),

    # Op3: Manual Packing A1 (11-3)
    ("Manual Packing A1", [
        ("Manual Packing Station A1", "WORKSTATION", "t_id_CT_HOPBHM_A_HM01"),
    ], 7.0, 6.0, 1, "MANUAL"),

    # Op4: AOI Carrier Conveyor (11-4)
    ("AOI Carrier Conveyor", [
        ("AOI Carrier Cross Conveyor", "OTHER", "t_id_TR7700L_QH_SI_AOI01"),
    ], 7.0, 20.0, 0, "OTHER"),

    # Op5: Manual Packing A2 (11-5, CT补=7)
    ("Manual Packing A2", [
        ("Manual Packing Station A2", "WORKSTATION", "t_id_CT_HOPBHM_A_HM02"),
    ], 7.0, 6.0, 1, "MANUAL"),

    # Op6: Cross Transfer (11-6, CT补=12)
    ("Cross Transfer", [
        ("Transfer Machine 2", "OTHER", "t_id_CT_HOPBCRO_CV02"),
    ], 12.0, 10.0, 0, "OTHER"),

    # Op7: Manual Packing B1 (11-7)
    ("Manual Packing B1", [
        ("Manual Packing Station B1", "WORKSTATION", "t_id_CT_HOPBHM_B_HM03"),
    ], 24.0, 6.0, 0, "MANUAL"),

    # Op8: Manual Packing B2 (11-8)
    ("Manual Packing B2", [
        ("Manual Packing Station B2", "WORKSTATION", "t_id_CT_HOPBHM_B_HM04"),
    ], 15.0, 10.0, 1, "MANUAL"),

    # Op9: Auto AOI Inspection (11-9) — BOTTLENECK
    ("Auto AOI Inspection", [
        ("Auto AOI Inspection Machine", "AOI", "t_id_CT_HOPBAOI_AOI02"),
    ], 45.5, 40.0, 0, "AOI"),

    # Op10: Manual Packing C1 (11-10)
    ("Manual Packing C1", [
        ("Manual Packing Station C1", "WORKSTATION", "t_id_CT_HOPBHM_C_HM05"),
    ], 7.0, 10.0, 1, "MANUAL"),

    # Op11: Manual Packing C2 (11-11)
    ("Manual Packing C2", [
        ("Manual Packing Station C2", "WORKSTATION", "t_id_CT_HOPBHM_C_HM06"),
    ], 7.0, 10.0, 1, "MANUAL"),

    # Op12: Edge Folding & Sealing (11-12)
    ("Edge Folding and Sealing", [
        ("Auto Edge Folding Sealer", "ROBOT", "t_id_CT_HOPBFWX1_X01"),
    ], 6.0, 6.0, 0, "OTHER"),

    # Op13: Corner Turning (11-13)
    ("Corner Turning", [
        ("Corner Turner", "OTHER", "t_id_CT_HOPBWST_W01"),
    ], 7.0, 6.0, 0, "OTHER"),

    # Op14: Top Corner Sealing (11-14, batch=2)
    ("Top Corner Sealing", [
        ("Auto Top Corner Sealer", "ROBOT", "t_id_CT_HOPBFWX2_X02"),
    ], 6.0, 3.3, 0, "OTHER"),

    # Op15: Seal Label Application (11-15, batch=2)
    ("Seal Label Application", [
        ("Auto Seal Label Applicator", "ROBOT", "t_id_CT_HOPBFKB_LB01"),
    ], 6.8, 5.0, 0, "OTHER"),

    # Op16: Palletizing (11-16, batch=2)
    ("Palletizing", [
        ("Auto Palletizer", "ROBOT", "t_id_CT_HOPBMD_MD01"),
    ], 45.0, 17.0, 0, "OTHER"),

    # Op17: Outbound Transfer (11-17, batch=2)
    ("Outbound Transfer", [
        ("Transfer Machine 3", "OTHER", "t_id_CT_HOPBYZ_CV03"),
    ], 9.98, 5.0, 0, "OTHER"),

    # Op18: Outbound Unloading (11-18, batch=2) — 2 equipment
    ("Outbound Unloading", [
        ("Carrier Machine (Outbound)", "ROBOT", "t_id_CT_HOPBLSJ_LD02"),
        ("Unloading Tray Rack", "ROBOT", "t_id_CT_HST_Pack_Trolley_TR02"),
    ], 22.5, 9.0, 0, "OTHER"),
]

# Panel qty for packaging line (一次几片): 1 for first 13 ops, 2 for last 5
PACK_PANEL_QTY = [1]*13 + [2]*5


def insert_line_data(line_id: str, line_code: str, data: list, panel_qtys: list[int] | None = None):
    """Insert operations, equipment, BOP, and BOP processes for one line."""
    bop_id = uid()
    db.add(BOP(
        bop_id=bop_id,
        product_id=product_id,
        line_id=line_id,
        bop_version="v1.0",
        is_active=True,
        created_by="seed_script",
    ))

    for seq, (op_name, eq_list, actual_ct, design_ct, workers, op_type) in enumerate(data, 1):
        op_id = uid()
        op_code = f"{line_code}_OP{seq:03d}"

        db.add(Operation(
            operation_id=op_id,
            line_id=line_id,
            operation_code=op_code,
            operation_name=op_name,
            sequence=seq,
            operation_type=op_type,
            is_key_operation=False,
            status="ACTIVE",
        ))

        for eq_idx, (eq_name, eq_type, prim_path) in enumerate(eq_list):
            eq_code = f"{line_code}_EQ{seq:03d}_{eq_idx + 1:02d}"
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

        panel_qty = panel_qtys[seq - 1] if panel_qtys else 1

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


# Insert Module line
insert_line_data(module_line_id, "L_HST_MODULE", MODULE_DATA)

# Insert Packaging line
insert_line_data(pack_line_id, "L_HST_PACK", PACK_DATA, PACK_PANEL_QTY)

# Update operation counts
db.query(ProductionLine).filter(ProductionLine.line_id == module_line_id).update(
    {"operation_count": len(MODULE_DATA)}
)
db.query(ProductionLine).filter(ProductionLine.line_id == pack_line_id).update(
    {"operation_count": len(PACK_DATA)}
)

# ============================================================================
# 7. Work Calendar + Shift
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
# 8. Simulation Plan + Production Tasks
# ============================================================================
plan_id = uid()
db.add(SimulationPlan(
    plan_id=plan_id,
    plan_name="Module + Packaging Line Baseline Evaluation",
    plan_description="Baseline simulation for Module assembly and Packaging lines with standard CT",
    factory_id=factory_id,
    status="DRAFT",
    enabled_simulators=["PRODUCTION", "LINE_BALANCE"],
    simulation_duration_hours=11.0,
    created_by="seed_script",
))

db.add(ProductionTask(
    task_id=uid(),
    plan_id=plan_id,
    stage_id=stage_id,
    line_id=module_line_id,
    product_code="PG548",
    plan_quantity=500,
    production_sequence=1,
    data_source="MANUAL_IMPORT",
))
db.add(ProductionTask(
    task_id=uid(),
    plan_id=plan_id,
    stage_id=stage_id,
    line_id=pack_line_id,
    product_code="PG548",
    plan_quantity=500,
    production_sequence=2,
    data_source="MANUAL_IMPORT",
))

# ============================================================================
# Commit
# ============================================================================
db.commit()

# Print summary
mod_ops = db.query(Operation).filter(Operation.line_id == module_line_id).count()
mod_eqs = db.query(Equipment).join(Operation).filter(Operation.line_id == module_line_id).count()
pack_ops = db.query(Operation).filter(Operation.line_id == pack_line_id).count()
pack_eqs = db.query(Equipment).join(Operation).filter(Operation.line_id == pack_line_id).count()

print(f"Seed complete:")
print(f"  Factory:     1 (Houston P9)")
print(f"  Stage:       1 (Back-End)")
print(f"  Lines:       2")
print(f"  Module line: {mod_ops} operations, {mod_eqs} equipment")
print(f"  Pack line:   {pack_ops} operations, {pack_eqs} equipment")
print(f"  Product:     1 (PG548)")
print(f"  BOPs:        2 (one per line)")
print(f"  Calendar:    1 day, 1 shift (11h)")
print(f"  Plan:        1 (DRAFT, 500 pcs per line)")
print(f"  Plan ID:     {plan_id}")

db.close()
