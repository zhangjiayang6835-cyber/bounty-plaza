"""Mexico City Tinaco Rainwater Harvester parametric CAD package."""

from packages.tinaco_collector.cad_generator import (
    Mesh3D,
    ParametricCadEngine,
)
from packages.tinaco_collector.drawings import (
    generate_ascii_engineering_drawing,
    generate_assembly_drawing_svg,
)
from packages.tinaco_collector.models import (
    AdjustableTinacoAdapter,
    BillOfMaterialsItem,
    CentralDrainOutlet,
    CollectorAssembly,
    PetalGeometry,
    SiteMeasurementRequirement,
)
from packages.tinaco_collector.specifications import (
    TINACO_SPECIFICATIONS_CATALOG,
    export_bom_markdown,
    export_checklist_markdown,
    generate_bill_of_materials,
    generate_site_measurement_checklist,
)
from packages.tinaco_collector.validator import (
    ValidationReport,
    validate_collector_geometry,
    validate_mesh_watertightness,
    validate_openscad_syntax,
    validate_step_syntax,
    validate_stl_syntax,
)

__all__ = [
    "AdjustableTinacoAdapter",
    "BillOfMaterialsItem",
    "CentralDrainOutlet",
    "CollectorAssembly",
    "Mesh3D",
    "ParametricCadEngine",
    "PetalGeometry",
    "SiteMeasurementRequirement",
    "TINACO_SPECIFICATIONS_CATALOG",
    "ValidationReport",
    "export_bom_markdown",
    "export_checklist_markdown",
    "generate_ascii_engineering_drawing",
    "generate_assembly_drawing_svg",
    "generate_bill_of_materials",
    "generate_site_measurement_checklist",
    "validate_collector_geometry",
    "validate_mesh_watertightness",
    "validate_openscad_syntax",
    "validate_step_syntax",
    "validate_stl_syntax",
]
