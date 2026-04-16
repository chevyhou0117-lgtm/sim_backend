"""Master data read-only API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.md import (
    BOP,
    BOPProcess,
    Equipment,
    Factory,
    Operation,
    Product,
    ProductionLine,
    Stage,
)
from app.schemas.md import (
    BOPOut,
    EquipmentOut,
    FactoryOut,
    OperationOut,
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
    return (
        db.query(Operation)
        .filter(Operation.line_id == line_id, Operation.status == "ACTIVE")
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


products_router = APIRouter(prefix="/products", tags=["Master Data"])


@products_router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.status == "ACTIVE").all()
