"""Master data read-only API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.md import (
    BOP,
    BOPProcess,
    Equipment,
    EquipmentFailureParam,
    Factory,
    Operation,
    OperationTransition,
    Product,
    ProductionLine,
    Stage,
)
from app.schemas.md import (
    BOPOut,
    EquipmentFailureParamOut,
    EquipmentOut,
    FactoryOut,
    LineEquipmentConfigItem,
    LineEquipmentConfigOut,
    OperationOut,
    OperationTransitionOut,
    ProductionLineOut,
    ProductOut,
    StageOut,
)

router = APIRouter(prefix="/factories", tags=["Master Data"])


@router.get("", response_model=list[FactoryOut])
def list_factories(db: Session = Depends(get_db)):
    return db.query(Factory).filter(Factory.status == "ACTIVE").all()


@router.get("/{factory_id}/stages", response_model=list[StageOut])
def list_stages(factory_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Stage)
        .filter(Stage.factory_id == factory_id, Stage.status == "ACTIVE")
        .order_by(Stage.sequence)
        .all()
    )


@router.get("/stages/{stage_id}/lines", response_model=list[ProductionLineOut])
def list_lines(stage_id: str, db: Session = Depends(get_db)):
    return (
        db.query(ProductionLine)
        .filter(ProductionLine.stage_id == stage_id, ProductionLine.status == "ACTIVE")
        .order_by(ProductionLine.sort_order)
        .all()
    )


@router.get("/lines/{line_id}/operations", response_model=list[OperationOut])
def list_operations(line_id: str, db: Session = Depends(get_db)):
    # Operation no longer has line_id; resolve via the line's active BOP → BOPProcess.
    return (
        db.query(Operation)
        .join(BOPProcess, BOPProcess.operation_id == Operation.operation_id)
        .join(BOP, BOP.bop_id == BOPProcess.bop_id)
        .filter(BOP.line_id == line_id, BOP.is_active == True, Operation.status == "ACTIVE")  # noqa: E712
        .order_by(Operation.sequence)
        .all()
    )


@router.get("/lines/{line_id}/bop", response_model=BOPOut | None)
def get_active_bop(line_id: str, db: Session = Depends(get_db)):
    bop = (
        db.query(BOP)
        .filter(BOP.line_id == line_id, BOP.is_active == True)  # noqa: E712
        .first()
    )
    if not bop:
        raise HTTPException(404, "No active BOP found for this line")
    return bop


@router.get("/operations/{operation_id}/equipment", response_model=list[EquipmentOut])
def list_equipment(operation_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Equipment)
        .filter(Equipment.operation_id == operation_id, Equipment.status == "ACTIVE")
        .order_by(Equipment.sort_order)
        .all()
    )


@router.get("/lines/{line_id}/transitions", response_model=list[OperationTransitionOut])
def list_transitions(line_id: str, db: Session = Depends(get_db)):
    """List operation transitions for the active BOP on a production line."""
    bop = (
        db.query(BOP)
        .filter(BOP.line_id == line_id, BOP.is_active == True)  # noqa: E712
        .first()
    )
    if not bop:
        return []
    return db.query(OperationTransition).filter(OperationTransition.bop_id == bop.bop_id).all()


@router.get("/{factory_id}/equipment-failure-params", response_model=list[EquipmentFailureParamOut])
def list_equipment_failure_params(factory_id: str, db: Session = Depends(get_db)):
    """List MTBF/MTTR params for all equipment in a factory."""
    return (
        db.query(EquipmentFailureParam)
        .join(Equipment, Equipment.equipment_id == EquipmentFailureParam.equipment_id)
        .join(Operation, Operation.operation_id == Equipment.operation_id)
        .join(Stage, Stage.stage_id == Operation.stage_id)
        .filter(Stage.factory_id == factory_id)
        .all()
    )


@router.get("/{factory_id}/equipment-config", response_model=LineEquipmentConfigOut)
def get_line_equipment_config(factory_id: str, db: Session = Depends(get_db)):
    """Aggregated payload for 产线设备配置 panel.

    Joins Equipment → Operation → active BOP → ProductionLine → Stage in a
    single query. An equipment may be reachable via multiple BOPs (multiple
    products) on the same line — we dedupe by equipment_id, keeping the first
    (line_sort_order, operation_sequence) row.
    """
    rows = (
        db.query(Equipment, Operation, ProductionLine, Stage)
        .join(Operation, Operation.operation_id == Equipment.operation_id)
        .join(BOPProcess, BOPProcess.operation_id == Operation.operation_id)
        .join(BOP, BOP.bop_id == BOPProcess.bop_id)
        .join(ProductionLine, ProductionLine.line_id == BOP.line_id)
        .join(Stage, Stage.stage_id == ProductionLine.stage_id)
        .filter(
            Stage.factory_id == factory_id,
            BOP.is_active == True,  # noqa: E712
            Equipment.status == "ACTIVE",
            Operation.status == "ACTIVE",
            ProductionLine.status == "ACTIVE",
        )
        .order_by(ProductionLine.sort_order, Operation.sequence, Equipment.sort_order)
        .all()
    )

    items: list[LineEquipmentConfigItem] = []
    seen_eq: set[str] = set()
    line_ids: set[str] = set()
    op_ids: set[str] = set()
    last_updated = None

    for eq, op, line, stage in rows:
        if eq.equipment_id in seen_eq:
            continue
        seen_eq.add(eq.equipment_id)
        line_ids.add(line.line_id)
        op_ids.add(op.operation_id)
        if eq.updated_at and (last_updated is None or eq.updated_at > last_updated):
            last_updated = eq.updated_at
        items.append(LineEquipmentConfigItem(
            equipment_id=eq.equipment_id,
            equipment_code=eq.equipment_code,
            equipment_name=eq.equipment_name,
            equipment_type=eq.equipment_type,
            manufacturer=eq.manufacturer,
            model_no=eq.model_no,
            standard_ct=eq.standard_ct,
            operation_id=op.operation_id,
            operation_code=op.operation_code,
            operation_name=op.operation_name,
            operation_sequence=op.sequence,
            line_id=line.line_id,
            line_code=line.line_code,
            line_name=line.line_name,
            stage_id=stage.stage_id,
            stage_name=stage.stage_name,
        ))

    return LineEquipmentConfigOut(
        factory_id=factory_id,
        line_count=len(line_ids),
        operation_count=len(op_ids),
        equipment_count=len(items),
        last_updated=last_updated,
        items=items,
    )


products_router = APIRouter(prefix="/products", tags=["Master Data"])


@products_router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.status == "ACTIVE").all()
