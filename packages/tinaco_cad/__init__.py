"""Parametric CAD and hydraulic simulation suite for tinaco rainwater collectors."""

from packages.tinaco_cad.params import CollectorParameters, TINACO_PRESETS
from packages.tinaco_cad.geometry import TriangleMesh, CADModelGenerator
from packages.tinaco_cad.hydraulics import HydraulicEngine, HydraulicAssessment
from packages.tinaco_cad.exporters import CADExporter

__all__ = [
    "CollectorParameters",
    "TINACO_PRESETS",
    "TriangleMesh",
    "CADModelGenerator",
    "HydraulicEngine",
    "HydraulicAssessment",
    "CADExporter",
]
