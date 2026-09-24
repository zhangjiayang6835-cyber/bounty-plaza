"""Parametric flower-shaped rainwater collector package for tinaco roof tanks."""

from packages.tinaco_rainwater_collector.cad_engine import CADGeometryEngine
from packages.tinaco_rainwater_collector.drawings import EngineeringDrawingGenerator
from packages.tinaco_rainwater_collector.hydraulics import HydraulicEngine, HydraulicResult
from packages.tinaco_rainwater_collector.models import (
    BillOfMaterials,
    BOMItem,
    DrainOutlet,
    Facet3D,
    FlowerCollectorConfig,
    MeasurementChecklist,
    PetalGeometry,
    Point3D,
    TinacoAdapter,
)
from packages.tinaco_rainwater_collector.settlement import SettlementEngine, SettlementReceipt

__all__ = [
    "BillOfMaterials",
    "BOMItem",
    "CADGeometryEngine",
    "DrainOutlet",
    "EngineeringDrawingGenerator",
    "Facet3D",
    "FlowerCollectorConfig",
    "HydraulicEngine",
    "HydraulicResult",
    "MeasurementChecklist",
    "PetalGeometry",
    "Point3D",
    "SettlementEngine",
    "SettlementReceipt",
    "TinacoAdapter",
]
