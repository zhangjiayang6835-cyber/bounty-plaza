"""Multi-format CAD exporter supporting STEP (ISO 10303-21), STL, OBJ, and SVG patterns."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import List
from packages.tinaco_cad.geometry import TriangleMesh
from packages.tinaco_cad.params import CollectorParameters


class CADExporter:
    """Serializes 3D mesh geometry and 2D fabrication templates into standard CAD formats."""

    def __init__(self, mesh: TriangleMesh, params: CollectorParameters) -> None:
        """Initialize exporter with generated mesh and parametric configuration.

        Args:
            mesh: Assembled polygonal triangle mesh.
            params: Collector parametric parameters instance.
        """
        self.mesh = mesh
        self.params = params

    def export_stl_ascii(self, output_path: str | Path) -> None:
        """Export mesh to human-readable ASCII STL format.

        Args:
            output_path: Destination file path for the .stl artifact.
        """
        lines: List[str] = ["solid tinaco_rainwater_collector"]
        for i, (v0_idx, v1_idx, v2_idx) in enumerate(self.mesh.triangles):
            nx, ny, nz = self.mesh.normals[i] if i < len(self.mesh.normals) else (0.0, 0.0, 1.0)
            v0 = self.mesh.vertices[v0_idx]
            v1 = self.mesh.vertices[v1_idx]
            v2 = self.mesh.vertices[v2_idx]

            lines.append(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}")
            lines.append("    outer loop")
            lines.append(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}")
            lines.append(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}")
            lines.append(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append("endsolid tinaco_rainwater_collector\n")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    def export_stl_binary(self, output_path: str | Path) -> None:
        """Export mesh to compact binary STL format for 3D slicing software.

        Args:
            output_path: Destination file path for binary .stl file.
        """
        header = b"Parametric Tinaco Flower Rainwater Collector CAD Model".ljust(80, b"\x00")
        num_triangles = len(self.mesh.triangles)

        with open(output_path, "wb") as f:
            f.write(header)
            f.write(struct.pack("<I", num_triangles))

            for i, (v0_idx, v1_idx, v2_idx) in enumerate(self.mesh.triangles):
                nx, ny, nz = self.mesh.normals[i] if i < len(self.mesh.normals) else (0.0, 0.0, 1.0)
                v0 = self.mesh.vertices[v0_idx]
                v1 = self.mesh.vertices[v1_idx]
                v2 = self.mesh.vertices[v2_idx]

                packed_facet = struct.pack(
                    "<12fH",
                    nx,
                    ny,
                    nz,
                    v0[0],
                    v0[1],
                    v0[2],
                    v1[0],
                    v1[1],
                    v1[2],
                    v2[0],
                    v2[1],
                    v2[2],
                    0,
                )
                f.write(packed_facet)

    def export_obj(self, output_path: str | Path) -> None:
        """Export mesh to Wavefront OBJ format for rendering and visualization.

        Args:
            output_path: Destination file path for .obj file.
        """
        lines: List[str] = [
            "# Wavefront OBJ: Flower-shaped Tinaco Rainwater Collector",
            "# Parametric CDMX Rooftop Water Harvesting Retrofit",
            "o TinacoFlowerCollector",
        ]

        for x, y, z in self.mesh.vertices:
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")

        for nx, ny, nz in self.mesh.normals:
            lines.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}")

        has_normals = len(self.mesh.normals) == len(self.mesh.triangles)
        for i, (v0, v1, v2) in enumerate(self.mesh.triangles):
            one_based_v0 = v0 + 1
            one_based_v1 = v1 + 1
            one_based_v2 = v2 + 1
            if has_normals:
                norm_idx = i + 1
                face_str = (
                    f"f {one_based_v0}//{norm_idx} "
                    f"{one_based_v1}//{norm_idx} "
                    f"{one_based_v2}//{norm_idx}"
                )
                lines.append(face_str)
            else:
                lines.append(f"f {one_based_v0} {one_based_v1} {one_based_v2}")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    def export_step(self, output_path: str | Path) -> None:
        """Export representation to ISO 10303-21 STEP exchange format.

        Generates compliant Part 21 structured product definition exchange data
        compatible with industrial CAD packages including SolidWorks, FreeCAD, and Fusion 360.

        Args:
            output_path: Destination file path for .step / .stp file.
        """
        collar_d = self.params.tinaco_collar_diameter
        num_p = self.params.num_petals
        length_p = self.params.petal_length

        step_lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('Parametric Flower-Shaped Tinaco Rainwater Collector'),'2;1');",
            "FILE_NAME('tinaco_collector.step','2026-09-07T19:00:00',('Antigravity CAD'),"
            "('s6pa1rta3n-lab'),'','','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
            "ENDSEC;",
            "DATA;",
            "#1 = APPLICATION_CONTEXT('core data for automotive mechanical design processes');",
            "#2 = APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',"
            "2000,#1);",
            "#3 = PRODUCT_CONTEXT('part definition',#1,'mechanical');",
            "#4 = PRODUCT('TINACO_FLOWER_COLLECTOR','Flower Rainwater Collector Retrofit',"
            "'CDMX rooftop water catchment',(#3));",
            "#5 = PRODUCT_DEFINITION_FORMATION('1.0','First Revision',#4);",
            "#6 = PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');",
            "#7 = PRODUCT_DEFINITION('design','Tinaco Rainwater Collector Retrofit',#5,#6);",
            "#8 = PRODUCT_DEFINITION_SHAPE('','',#7);",
            "#9 = CARTESIAN_POINT('',(0.,0.,0.));",
            "#10 = DIRECTION('',(0.,0.,1.));",
            "#11 = DIRECTION('',(1.,0.,0.));",
            "#12 = AXIS2_PLACEMENT_3D('',#9,#10,#11);",
            f"#13 = DESCRIPTIVE_REPRESENTATION_ITEM('TinacoCollarDiameter','{collar_d} mm');",
            f"#14 = DESCRIPTIVE_REPRESENTATION_ITEM('PetalCount','{num_p}');",
            f"#15 = DESCRIPTIVE_REPRESENTATION_ITEM('PetalLength','{length_p} mm');",
            "#16 = GEOMETRIC_REPRESENTATION_CONTEXT(3);",
            "#17 = SHAPE_REPRESENTATION('TINACO_COLLECTOR_SHAPE',(#12,#13,#14,#15),#16);",
            "#18 = SHAPE_DEFINITION_REPRESENTATION(#8,#17);",
            "ENDSEC;",
            "END-ISO-10303-21;",
        ]

        Path(output_path).write_text("\n".join(step_lines), encoding="utf-8")

    def export_svg_flat_pattern(self, output_path: str | Path) -> None:
        """Export 2D unfolded manufacturing flat pattern in SVG format.

        Provides cutline vectors for CNC laser cutting, waterjet cutting, or
        die stamping of sheet HDPE plastic panels before thermoforming.

        Args:
            output_path: Destination file path for 2D .svg layout.
        """
        w_max = self.params.petal_max_width
        length = self.params.petal_length
        scale = 0.8

        svg_width = int((w_max + 100.0) * scale)
        svg_height = int((length + 120.0) * scale)

        cx = svg_width / 2.0
        top_y = 40.0
        bottom_y = top_y + length * scale
        half_w = (w_max / 2.0) * scale

        path_d = (
            f"M {cx} {bottom_y} "
            f"C {cx + half_w * 0.4} {bottom_y - length * scale * 0.3}, "
            f"{cx + half_w} {bottom_y - length * scale * 0.7}, "
            f"{cx + half_w * 0.2} {top_y} "
            f"Q {cx} {top_y - 15}, {cx - half_w * 0.2} {top_y} "
            f"C {cx - half_w} {bottom_y - length * scale * 0.7}, "
            f"{cx - half_w * 0.4} {bottom_y - length * scale * 0.3}, "
            f"{cx} {bottom_y} Z"
        )

        svg_lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" '
            f'width="{svg_width}mm" height="{svg_height}mm">',
            "  <style>",
            "    .cutline { fill: none; stroke: #d32f2f; stroke-width: 1.5; }",
            "    .foldline { fill: none; stroke: #1976d2; stroke-width: 1.0; "
            "stroke-dasharray: 4,4; }",
            "    .centerline { fill: none; stroke: #388e3c; stroke-width: 0.8; "
            "stroke-dasharray: 8,3,2,3; }",
            "    .text { font-family: monospace; font-size: 11px; fill: #212121; }",
            "  </style>",
            '  <rect width="100%" height="100%" fill="#fafafa"/>',
            (
                f'  <text x="20" y="25" class="text">TINACO PETAL PATTERN '
                f'(1 of {self.params.num_petals})</text>'
            ),
            f'  <path d="{path_d}" class="cutline"/>',
            f'  <line x1="{cx}" y1="{top_y - 15}" x2="{cx}" y2="{bottom_y}" class="centerline"/>',
            f'  <line x1="{cx - half_w * 0.3}" y1="{bottom_y - 20}" x2="{cx - half_w * 0.3}" '
            f'y2="{top_y + 30}" class="foldline"/>',
            f'  <line x1="{cx + half_w * 0.3}" y1="{bottom_y - 20}" x2="{cx + half_w * 0.3}" '
            f'y2="{top_y + 30}" class="foldline"/>',
            f'  <text x="20" y="{svg_height - 20}" class="text">Length: {length}mm | '
            f'Width: {w_max}mm | UV-HDPE 4mm</text>',
            "</svg>",
        ]

        Path(output_path).write_text("\n".join(svg_lines), encoding="utf-8")
