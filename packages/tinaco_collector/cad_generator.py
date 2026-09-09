"""Parametric 3D CAD geometry engine, STL and STEP exporters for tinaco collector."""

from dataclasses import dataclass, field
import datetime
import math
import struct
from typing import Any, Dict, List, Optional, Set, Tuple

from packages.tinaco_collector.models import (
    AdjustableTinacoAdapter,
    CentralDrainOutlet,
    CollectorAssembly,
    PetalGeometry,
)


@dataclass
class Mesh3D:
    """Represents a watertight 3D triangular surface mesh."""

    name: str = "cad_mesh"
    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    faces: List[Tuple[int, int, int]] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)

    def recompute_normals(self) -> None:
        """Calculate face normal unit vectors via vector cross product."""
        computed_normals: List[Tuple[float, float, float]] = []
        for v0_idx, v1_idx, v2_idx in self.faces:
            p0 = self.vertices[v0_idx]
            p1 = self.vertices[v1_idx]
            p2 = self.vertices[v2_idx]

            u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

            nx = u[1] * v[2] - u[2] * v[1]
            ny = u[2] * v[0] - u[0] * v[2]
            nz = u[0] * v[1] - u[1] * v[0]

            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length > 1e-9:
                computed_normals.append((nx / length, ny / length, nz / length))
            else:
                computed_normals.append((0.0, 0.0, 1.0))
        self.normals = computed_normals

    @property
    def surface_area(self) -> float:
        """Calculate total surface area of all triangular faces in square millimeters."""
        total_area = 0.0
        for v0_idx, v1_idx, v2_idx in self.faces:
            p0 = self.vertices[v0_idx]
            p1 = self.vertices[v1_idx]
            p2 = self.vertices[v2_idx]

            u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])

            cross_x = u[1] * v[2] - u[2] * v[1]
            cross_y = u[2] * v[0] - u[0] * v[2]
            cross_z = u[0] * v[1] - u[1] * v[0]
            face_area = 0.5 * math.sqrt(cross_x * cross_x + cross_y * cross_y + cross_z * cross_z)
            total_area += face_area
        return total_area

    @property
    def signed_volume(self) -> float:
        """Calculate signed enclosed volume using divergence theorem in cubic millimeters."""
        total_vol = 0.0
        for v0_idx, v1_idx, v2_idx in self.faces:
            p0 = self.vertices[v0_idx]
            p1 = self.vertices[v1_idx]
            p2 = self.vertices[v2_idx]

            vol6 = (
                p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])
            )
            total_vol += vol6
        return total_vol / 6.0

    @property
    def bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Calculate minimum and maximum coordinate bounds."""
        if not self.vertices:
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

    def is_closed_manifold(self) -> bool:
        """Verify if mesh is topologically closed with 2-manifold edges."""
        if not self.faces or not self.vertices:
            return False
        edge_counts: Dict[Tuple[int, int], int] = {}
        for v0, v1, v2 in self.faces:
            edges = [
                (min(v0, v1), max(v0, v1)),
                (min(v1, v2), max(v1, v2)),
                (min(v2, v0), max(v2, v0)),
            ]
            for edge in edges:
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        for count in edge_counts.values():
            if count != 2:
                return False
        return True

    def to_stl_ascii(self, custom_name: Optional[str] = None) -> str:
        """Generate ASCII format STL representation.

        Args:
            custom_name: Solid identifier in STL header.

        Returns:
            Complete ASCII STL string.
        """
        if not self.normals or len(self.normals) != len(self.faces):
            self.recompute_normals()

        solid_name = custom_name or self.name
        lines = [f"solid {solid_name}"]
        for (v0_idx, v1_idx, v2_idx), norm in zip(self.faces, self.normals):
            p0 = self.vertices[v0_idx]
            p1 = self.vertices[v1_idx]
            p2 = self.vertices[v2_idx]
            lines.append(f"  facet normal {norm[0]:.6e} {norm[1]:.6e} {norm[2]:.6e}")
            lines.append("    outer loop")
            lines.append(f"      vertex {p0[0]:.6e} {p0[1]:.6e} {p0[2]:.6e}")
            lines.append(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}")
            lines.append(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}")
            lines.append("    endloop")
            lines.append("  endfacet")
        lines.append(f"endsolid {solid_name}\n")
        return "\n".join(lines)

    def to_stl_binary(self) -> bytes:
        """Generate standard binary format STL representation conforming to specification."""
        if not self.normals or len(self.normals) != len(self.faces):
            self.recompute_normals()

        header = f"Binary STL Export: {self.name[:60]}".encode("ascii").ljust(80, b"\0")
        face_count = len(self.faces)
        buffer = bytearray(header)
        buffer.extend(struct.pack("<I", face_count))

        for (v0_idx, v1_idx, v2_idx), norm in zip(self.faces, self.normals):
            p0 = self.vertices[v0_idx]
            p1 = self.vertices[v1_idx]
            p2 = self.vertices[v2_idx]
            buffer.extend(
                struct.pack(
                    "<12fH",
                    norm[0], norm[1], norm[2],
                    p0[0], p0[1], p0[2],
                    p1[0], p1[1], p1[2],
                    p2[0], p2[1], p2[2],
                    0,
                )
            )
        return bytes(buffer)

    def to_step(self, product_id: Optional[str] = None) -> str:
        """Generate ISO 10303-21 STEP physical file containing faceted B-rep solid.

        Args:
            product_id: Product nomenclature in STEP product definition.

        Returns:
            Compliant ISO 10303-21 STEP ASCII physical file format string.
        """
        if not self.normals or len(self.normals) != len(self.faces):
            self.recompute_normals()

        name = product_id or self.name
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        lines: List[str] = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('Parametric CAD Model', 'Faceted B-Rep Solid'), '2;1');",
            f"FILE_NAME('{name}.step', '{timestamp}', ('Automated CAD Generator'), ('CDMX Rooftop Water Initiative'), 'Parametric Engine 2.0', 'Open CAD Suite', '');",
            "FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));",
            "ENDSEC;",
            "DATA;",
            "#1 = APPLICATION_CONTEXT('configuration controlled 3d designs of mechanical parts and assemblies');",
            "#2 = APPLICATION_PROTOCOL_DEFINITION('international standard', 'config_control_design', 1994, #1);",
            f"#3 = PRODUCT('{name}', '{name}', 'Flower-Shaped Rainwater Collector Component', (#4));",
            "#4 = PRODUCT_CONTEXT('', #1, 'mechanical');",
            f"#5 = PRODUCT_DEFINITION_FORMATION('1', 'First Revision', #3);",
            "#6 = PRODUCT_DEFINITION_CONTEXT('part definition', #1, 'design');",
            f"#7 = PRODUCT_DEFINITION('design', 'Complete Component Model', #5, #6);",
            "#8 = PRODUCT_DEFINITION_SHAPE('shape representation', '', #7);",
            "#9 = CARTESIAN_POINT('origin', (0., 0., 0.));",
            "#10 = DIRECTION('dir_z', (0., 0., 1.));",
            "#11 = DIRECTION('dir_x', (1., 0., 0.));",
            "#12 = AXIS2_PLACEMENT_3D('placement', #9, #10, #11);",
            "#13 = UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-05), #17, 'closure', 'Maximum tolerance');",
            "#14 = (GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#13)) GLOBAL_UNIT_ASSIGNED_CONTEXT((#17, #18, #19)) REPRESENTATION_CONTEXT('3D', '3D Workspace Context'));",
            "#15 = SI_UNIT(.MILLI., .METRE.);",
            "#16 = LENGTH_UNIT();",
            "#17 = (CONVERSION_BASED_UNIT('MILLIMETRE', #20) LENGTH_UNIT() NAMED_UNIT(#21));",
            "#18 = (NAMED_UNIT(#22) PLANE_ANGLE_UNIT() SI_UNIT($, .RADIAN.));",
            "#19 = (NAMED_UNIT(#22) SOLID_ANGLE_UNIT() SI_UNIT($, .STERADIAN.));",
            "#20 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-03), #15);",
            "#21 = DIMENSIONAL_EXPOSITIONS(1., 0., 0., 0., 0., 0., 0.);",
            "#22 = DIMENSIONAL_EXPOSITIONS(0., 0., 0., 0., 0., 0., 0.);",
        ]

        next_id = 30
        vert_id_map: Dict[int, int] = {}
        for idx, (vx, vy, vz) in enumerate(self.vertices):
            vert_id = next_id
            cartesian_id = next_id + 1
            lines.append(f"#{cartesian_id} = CARTESIAN_POINT('', ({vx:.4f}, {vy:.4f}, {vz:.4f}));")
            lines.append(f"#{vert_id} = VERTEX_POINT('', #{cartesian_id});")
            vert_id_map[idx] = vert_id
            next_id += 2

        face_entities: List[int] = []
        for face_idx, (v0, v1, v2) in enumerate(self.faces):
            p0_id = vert_id_map[v0]
            p1_id = vert_id_map[v1]
            p2_id = vert_id_map[v2]

            norm = self.normals[face_idx]
            dir_id = next_id
            lines.append(f"#{dir_id} = DIRECTION('', ({norm[0]:.6f}, {norm[1]:.6f}, {norm[2]:.6f}));")
            next_id += 1

            loop_id = next_id
            loop_points = f"#{p0_id}, #{p1_id}, #{p2_id}"
            lines.append(f"#{loop_id} = POLY_LOOP('', ({loop_points}));")
            next_id += 1

            bound_id = next_id
            lines.append(f"#{bound_id} = FACE_OUTER_BOUND('', #{loop_id}, .T.);")
            next_id += 1

            face_id = next_id
            lines.append(f"#{face_id} = ADVANCED_FACE('', (#{bound_id}), #12, .T.);")
            face_entities.append(face_id)
            next_id += 1

        shell_id = next_id
        faces_str = ", ".join(f"#{fid}" for fid in face_entities)
        lines.append(f"#{shell_id} = CLOSED_SHELL('', ({faces_str}));")
        next_id += 1

        brep_id = next_id
        lines.append(f"#{brep_id} = MANIFOLD_SOLID_BREP('{name}_brep', #{shell_id});")
        next_id += 1

        shape_rep_id = next_id
        lines.append(
            f"#{shape_rep_id} = ADVANCED_BREP_SHAPE_REPRESENTATION('{name}_shape', (#{brep_id}, #12), #14);"
        )
        lines.append(f"#8 = SHAPE_DEFINITION_REPRESENTATION(#8, #{shape_rep_id});")

        lines.append("ENDSEC;")
        lines.append("END-ISO-10303-21;\n")
        return "\n".join(lines)


class ParametricCadEngine:
    """Mathematical generator for flower-shaped rainwater collector geometry."""

    @staticmethod
    def generate_cylinder_prism_mesh(
        bottom_radius: float,
        top_radius: float,
        height: float,
        z_offset: float = 0.0,
        radial_segments: int = 32,
        name: str = "cylinder",
    ) -> Mesh3D:
        """Create a frustum cylinder mesh with top and bottom caps."""
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []

        vertices.append((0.0, 0.0, z_offset))
        for i in range(radial_segments):
            angle = (2.0 * math.pi * i) / radial_segments
            x = bottom_radius * math.cos(angle)
            y = bottom_radius * math.sin(angle)
            vertices.append((x, y, z_offset))

        vertices.append((0.0, 0.0, z_offset + height))
        for i in range(radial_segments):
            angle = (2.0 * math.pi * i) / radial_segments
            x = top_radius * math.cos(angle)
            y = top_radius * math.sin(angle)
            vertices.append((x, y, z_offset + height))

        bottom_center = 0
        top_center = radial_segments + 1

        for i in range(radial_segments):
            curr_b = 1 + i
            next_b = 1 + ((i + 1) % radial_segments)
            faces.append((bottom_center, next_b, curr_b))

        top_start = radial_segments + 2
        for i in range(radial_segments):
            curr_t = top_start + i
            next_t = top_start + ((i + 1) % radial_segments)
            faces.append((top_center, curr_t, next_t))

        for i in range(radial_segments):
            curr_b = 1 + i
            next_b = 1 + ((i + 1) % radial_segments)
            curr_t = top_start + i
            next_t = top_start + ((i + 1) % radial_segments)

            faces.append((curr_b, next_b, next_t))
            faces.append((curr_b, next_t, curr_t))

        mesh = Mesh3D(name=name, vertices=vertices, faces=faces)
        mesh.recompute_normals()
        return mesh

    @staticmethod
    def generate_petal_blade_mesh(
        petals: PetalGeometry,
        petal_index: int,
        radial_steps: int = 10,
        arc_steps: int = 12,
    ) -> Mesh3D:
        """Generate 3D watertight solid representing one sloped flower petal blade."""
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []

        sector_span_deg = (360.0 / petals.petal_count) + petals.petal_overlap_deg
        center_angle_deg = (360.0 / petals.petal_count) * petal_index
        start_angle_deg = center_angle_deg - (sector_span_deg / 2.0)
        end_angle_deg = center_angle_deg + (sector_span_deg / 2.0)

        slope_rad = math.radians(petals.inward_slope_deg)
        r_in = petals.inner_radius_mm
        r_out = petals.outer_radius_mm
        thick = petals.wall_thickness_mm
        lip_h = petals.rim_lip_height_mm

        grid_top: List[List[int]] = []
        for r_step in range(radial_steps + 1):
            t_r = float(r_step) / float(radial_steps)
            r = r_in + t_r * (r_out - r_in)
            z_base = (r - r_in) * math.tan(slope_rad)
            row_indices: List[int] = []
            for a_step in range(arc_steps + 1):
                t_a = float(a_step) / float(arc_steps)
                angle_deg = start_angle_deg + t_a * (end_angle_deg - start_angle_deg)
                angle_rad = math.radians(angle_deg)

                profile_curvature = math.sin(t_a * math.pi) * 20.0 * (t_r**1.5)
                lip_elevation = (t_r**4) * lip_h * (1.0 - math.sin(t_a * math.pi) * 0.4)
                z = z_base - profile_curvature + lip_elevation

                x = r * math.cos(angle_rad)
                y = r * math.sin(angle_rad)
                row_indices.append(len(vertices))
                vertices.append((x, y, z))
            grid_top.append(row_indices)

        grid_bottom: List[List[int]] = []
        for r_step in range(radial_steps + 1):
            t_r = float(r_step) / float(radial_steps)
            r = r_in + t_r * (r_out - r_in)
            z_base = (r - r_in) * math.tan(slope_rad)
            row_indices = []
            for a_step in range(arc_steps + 1):
                t_a = float(a_step) / float(arc_steps)
                angle_deg = start_angle_deg + t_a * (end_angle_deg - start_angle_deg)
                angle_rad = math.radians(angle_deg)

                profile_curvature = math.sin(t_a * math.pi) * 20.0 * (t_r**1.5)
                lip_elevation = (t_r**4) * lip_h * (1.0 - math.sin(t_a * math.pi) * 0.4)
                z = z_base - profile_curvature + lip_elevation - thick

                x = r * math.cos(angle_rad)
                y = r * math.sin(angle_rad)
                row_indices.append(len(vertices))
                vertices.append((x, y, z))
            grid_bottom.append(row_indices)

        for r in range(radial_steps):
            for a in range(arc_steps):
                p00 = grid_top[r][a]
                p10 = grid_top[r + 1][a]
                p11 = grid_top[r + 1][a + 1]
                p01 = grid_top[r][a + 1]
                faces.append((p00, p10, p11))
                faces.append((p00, p11, p01))

        for r in range(radial_steps):
            for a in range(arc_steps):
                p00 = grid_bottom[r][a]
                p10 = grid_bottom[r + 1][a]
                p11 = grid_bottom[r + 1][a + 1]
                p01 = grid_bottom[r][a + 1]
                faces.append((p00, p11, p10))
                faces.append((p00, p01, p11))

        for a in range(arc_steps):
            t0 = grid_top[0][a]
            t1 = grid_top[0][a + 1]
            b0 = grid_bottom[0][a]
            b1 = grid_bottom[0][a + 1]
            faces.append((t0, b0, b1))
            faces.append((t0, b1, t1))

        for a in range(arc_steps):
            t0 = grid_top[radial_steps][a]
            t1 = grid_top[radial_steps][a + 1]
            b0 = grid_bottom[radial_steps][a]
            b1 = grid_bottom[radial_steps][a + 1]
            faces.append((t0, t1, b1))
            faces.append((t0, b1, b0))

        for r in range(radial_steps):
            t0 = grid_top[r][0]
            t1 = grid_top[r + 1][0]
            b0 = grid_bottom[r][0]
            b1 = grid_bottom[r + 1][0]
            faces.append((t0, t1, b1))
            faces.append((t0, b1, b0))

        for r in range(radial_steps):
            t0 = grid_top[r][arc_steps]
            t1 = grid_top[r + 1][arc_steps]
            b0 = grid_bottom[r][arc_steps]
            b1 = grid_bottom[r + 1][arc_steps]
            faces.append((t0, b0, b1))
            faces.append((t0, b1, t1))

        mesh = Mesh3D(name=f"petal_{petal_index}", vertices=vertices, faces=faces)
        mesh.recompute_normals()
        return mesh

    @staticmethod
    def generate_flower_collector_mesh(
        petals: PetalGeometry,
        drain: CentralDrainOutlet,
    ) -> Mesh3D:
        """Create consolidated watertight solid of flower collector funnel array."""
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []

        rings = [
            (drain.neck_radius_mm, -drain.funnel_depth_mm, 0.0),
            (drain.neck_radius_mm + 15.0, -drain.funnel_depth_mm + 30.0, 0.0),
            (drain.throat_radius_mm * 0.7, -drain.funnel_depth_mm * 0.35, 0.0),
            (drain.throat_radius_mm, 0.0, 0.0),
            (petals.inner_radius_mm * 1.5, petals.vertical_drop_mm * 0.25, 0.0),
            (petals.inner_radius_mm * 2.5, petals.vertical_drop_mm * 0.60, 0.0),
            (petals.outer_radius_mm, petals.vertical_drop_mm + petals.rim_lip_height_mm, 35.0),
        ]

        angular_segments = 64
        top_grid: List[List[int]] = []
        for radius, z_level, undulation in rings:
            row: List[int] = []
            for seg in range(angular_segments):
                angle = (2.0 * math.pi * seg) / angular_segments
                petal_mod = math.cos(angle * petals.petal_count)
                r_effective = radius + undulation * 0.15 * petal_mod
                z_effective = z_level + undulation * 0.35 * petal_mod
                row.append(len(vertices))
                vertices.append((r_effective * math.cos(angle), r_effective * math.sin(angle), z_effective))
            top_grid.append(row)

        bottom_grid: List[List[int]] = []
        thick = petals.wall_thickness_mm
        for radius, z_level, undulation in rings:
            row = []
            for seg in range(angular_segments):
                angle = (2.0 * math.pi * seg) / angular_segments
                petal_mod = math.cos(angle * petals.petal_count)
                r_effective = max(10.0, radius - thick + undulation * 0.15 * petal_mod)
                z_effective = z_level - thick + undulation * 0.35 * petal_mod
                row.append(len(vertices))
                vertices.append((r_effective * math.cos(angle), r_effective * math.sin(angle), z_effective))
            bottom_grid.append(row)

        for ring_idx in range(len(rings) - 1):
            for seg in range(angular_segments):
                next_seg = (seg + 1) % angular_segments
                p00 = top_grid[ring_idx][seg]
                p10 = top_grid[ring_idx + 1][seg]
                p11 = top_grid[ring_idx + 1][next_seg]
                p01 = top_grid[ring_idx][next_seg]
                faces.append((p00, p10, p11))
                faces.append((p00, p11, p01))

        for ring_idx in range(len(rings) - 1):
            for seg in range(angular_segments):
                next_seg = (seg + 1) % angular_segments
                p00 = bottom_grid[ring_idx][seg]
                p10 = bottom_grid[ring_idx + 1][seg]
                p11 = bottom_grid[ring_idx + 1][next_seg]
                p01 = bottom_grid[ring_idx][next_seg]
                faces.append((p00, p11, p10))
                faces.append((p00, p01, p11))

        last_ring = len(rings) - 1
        for seg in range(angular_segments):
            next_seg = (seg + 1) % angular_segments
            t0 = top_grid[last_ring][seg]
            t1 = top_grid[last_ring][next_seg]
            b0 = bottom_grid[last_ring][seg]
            b1 = bottom_grid[last_ring][next_seg]
            faces.append((t0, t1, b1))
            faces.append((t0, b1, b0))

        for seg in range(angular_segments):
            next_seg = (seg + 1) % angular_segments
            t0 = top_grid[0][seg]
            t1 = top_grid[0][next_seg]
            b0 = bottom_grid[0][seg]
            b1 = bottom_grid[0][next_seg]
            faces.append((t0, b0, b1))
            faces.append((t0, b1, t1))

        mesh = Mesh3D(name="tinaco_flower_collector", vertices=vertices, faces=faces)
        mesh.recompute_normals()
        return mesh

    @staticmethod
    def generate_adjustable_adapter_mesh(
        adapter: AdjustableTinacoAdapter,
        drain: CentralDrainOutlet,
    ) -> Mesh3D:
        """Create 3D watertight mesh of the adjustable tinaco adapter collar."""
        vertices: List[Tuple[float, float, float]] = []
        faces: List[Tuple[int, int, int]] = []

        r_inner = adapter.nominal_diameter_mm / 2.0
        r_outer = r_inner + adapter.collar_thickness_mm
        r_flange = r_outer + 35.0
        h_collar = adapter.collar_height_mm
        z_top = -drain.funnel_depth_mm
        z_bottom = z_top - h_collar

        segments = 64
        quadrant_span = segments // adapter.segment_count

        ring_specs = [
            (r_inner, z_bottom),
            (r_outer, z_bottom),
            (r_outer, z_top - 20.0),
            (r_flange, z_top - 20.0),
            (r_flange, z_top),
            (r_inner, z_top),
        ]

        profile_grids: List[List[int]] = []
        for rad, z_val in ring_specs:
            row: List[int] = []
            for seg in range(segments):
                angle = (2.0 * math.pi * seg) / segments
                x = rad * math.cos(angle)
                y = rad * math.sin(angle)
                row.append(len(vertices))
                vertices.append((x, y, z_val))
            profile_grids.append(row)

        for p_idx in range(len(ring_specs) - 1):
            for seg in range(segments):
                next_seg = (seg + 1) % segments
                p00 = profile_grids[p_idx][seg]
                p10 = profile_grids[p_idx + 1][seg]
                p11 = profile_grids[p_idx + 1][next_seg]
                p01 = profile_grids[p_idx][next_seg]
                faces.append((p00, p10, p11))
                faces.append((p00, p11, p01))

        last_p = len(ring_specs) - 1
        for seg in range(segments):
            next_seg = (seg + 1) % segments
            p0 = profile_grids[last_p][seg]
            p1 = profile_grids[last_p][next_seg]
            q0 = profile_grids[0][seg]
            q1 = profile_grids[0][next_seg]
            faces.append((p0, p1, q1))
            faces.append((p0, q1, q0))

        mesh = Mesh3D(name="tinaco_adjustable_adapter", vertices=vertices, faces=faces)
        mesh.recompute_normals()
        return mesh

    @staticmethod
    def generate_complete_assembly_mesh(assembly: CollectorAssembly) -> Mesh3D:
        """Unify collector funnel and adjustable adapter into a consolidated solid."""
        collector_mesh = ParametricCadEngine.generate_flower_collector_mesh(
            assembly.petals,
            assembly.drain,
        )
        adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(
            assembly.adapter,
            assembly.drain,
        )

        merged_vertices = list(collector_mesh.vertices)
        merged_faces = list(collector_mesh.faces)
        vert_offset = len(merged_vertices)

        for vx, vy, vz in adapter_mesh.vertices:
            merged_vertices.append((vx, vy, vz))

        for v0, v1, v2 in adapter_mesh.faces:
            merged_faces.append((v0 + vert_offset, v1 + vert_offset, v2 + vert_offset))

        assembly_mesh = Mesh3D(
            name="tinaco_flower_assembly",
            vertices=merged_vertices,
            faces=merged_faces,
        )
        assembly_mesh.recompute_normals()
        return assembly_mesh

    @staticmethod
    def generate_openscad_source(assembly: CollectorAssembly) -> str:
        """Generate parametric OpenSCAD source file with zero inline comments."""
        lines = [
            "$fn = 72;",
            f"PETAL_COUNT = {assembly.petals.petal_count};",
            f"OUTER_RADIUS = {assembly.petals.outer_radius_mm};",
            f"INNER_RADIUS = {assembly.petals.inner_radius_mm};",
            f"SLOPE_DEG = {assembly.petals.inward_slope_deg};",
            f"WALL_THICKNESS = {assembly.petals.wall_thickness_mm};",
            f"LIP_HEIGHT = {assembly.petals.rim_lip_height_mm};",
            f"THROAT_DIAMETER = {assembly.drain.throat_diameter_mm};",
            f"DRAIN_NECK_DIAMETER = {assembly.drain.drain_neck_diameter_mm};",
            f"FUNNEL_DEPTH = {assembly.drain.funnel_depth_mm};",
            f"ADAPTER_NOMINAL_DIA = {assembly.adapter.nominal_diameter_mm};",
            f"ADAPTER_MIN_DIA = {assembly.adapter.min_clamp_diameter_mm};",
            f"ADAPTER_MAX_DIA = {assembly.adapter.max_clamp_diameter_mm};",
            f"ADAPTER_HEIGHT = {assembly.adapter.collar_height_mm};",
            f"ADAPTER_THICKNESS = {assembly.adapter.collar_thickness_mm};",
            "",
            "module single_petal_sweep() {",
            "    span_angle = (360.0 / PETAL_COUNT) + 6.0;",
            "    rotate_extrude(angle = span_angle, convexity = 10)",
            "    translate([INNER_RADIUS, 0, 0])",
            "    polygon(points = [",
            "        [0, 0],",
            "        [OUTER_RADIUS - INNER_RADIUS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG)],",
            "        [OUTER_RADIUS - INNER_RADIUS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) + LIP_HEIGHT],",
            "        [OUTER_RADIUS - INNER_RADIUS - WALL_THICKNESS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) + LIP_HEIGHT],",
            "        [OUTER_RADIUS - INNER_RADIUS - WALL_THICKNESS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) - WALL_THICKNESS],",
            "        [0, -WALL_THICKNESS]",
            "    ]);",
            "}",
            "",
            "module flower_petals_array() {",
            "    for (i = [0 : PETAL_COUNT - 1]) {",
            "        rotate([0, 0, i * (360.0 / PETAL_COUNT)])",
            "        single_petal_sweep();",
            "    }",
            "}",
            "",
            "module central_drain_funnel() {",
            "    difference() {",
            "        cylinder(h = FUNNEL_DEPTH, r1 = DRAIN_NECK_DIAMETER / 2.0 + WALL_THICKNESS, r2 = THROAT_DIAMETER / 2.0 + WALL_THICKNESS, center = false);",
            "        translate([0, 0, -1])",
            "        cylinder(h = FUNNEL_DEPTH + 2, r1 = DRAIN_NECK_DIAMETER / 2.0, r2 = THROAT_DIAMETER / 2.0, center = false);",
            "    }",
            "}",
            "",
            "module anti_vortex_vanes() {",
            "    for (j = [0 : 3]) {",
            "        rotate([0, 0, j * 90])",
            "        translate([0, -WALL_THICKNESS / 2.0, 0])",
            "        cube([THROAT_DIAMETER / 2.0 - 10.0, WALL_THICKNESS, FUNNEL_DEPTH * 0.75]);",
            "    }",
            "}",
            "",
            "module adjustable_tinaco_adapter_collar() {",
            "    r_in = ADAPTER_NOMINAL_DIA / 2.0;",
            "    r_out = r_in + ADAPTER_THICKNESS;",
            "    difference() {",
            "        union() {",
            "            cylinder(h = ADAPTER_HEIGHT, r = r_out, center = false);",
            "            translate([0, 0, ADAPTER_HEIGHT - 20])",
            "            cylinder(h = 20, r = r_out + 35, center = false);",
            "        }",
            "        translate([0, 0, -2])",
            "        cylinder(h = ADAPTER_HEIGHT + 4, r = r_in, center = false);",
            "        for (s = [0 : 3]) {",
            "            rotate([0, 0, s * 90])",
            "            translate([-10, -5, -1])",
            "            cube([r_out + 50, 10, ADAPTER_HEIGHT + 2]);",
            "        }",
            "    }",
            "}",
            "",
            "module debris_filter_screen() {",
            "    difference() {",
            "        cylinder(h = 10, r = DRAIN_NECK_DIAMETER / 2.0 + 5, center = false);",
            "        translate([0, 0, -1])",
            "        cylinder(h = 12, r = DRAIN_NECK_DIAMETER / 2.0 - 8, center = false);",
            "    }",
            "}",
            "",
            "module tinaco_rainwater_harvester_assembly() {",
            "    color([0.2, 0.7, 0.9, 0.85])",
            "    flower_petals_array();",
            "",
            "    color([0.15, 0.5, 0.8, 1.0])",
            "    translate([0, 0, -FUNNEL_DEPTH])",
            "    union() {",
            "        central_drain_funnel();",
            "        anti_vortex_vanes();",
            "    }",
            "",
            "    color([0.3, 0.3, 0.35, 1.0])",
            "    translate([0, 0, -FUNNEL_DEPTH - ADAPTER_HEIGHT])",
            "    adjustable_tinaco_adapter_collar();",
            "",
            "    color([0.8, 0.8, 0.85, 1.0])",
            "    translate([0, 0, -FUNNEL_DEPTH + 15])",
            "    debris_filter_screen();",
            "}",
            "",
            "tinaco_rainwater_harvester_assembly();",
            "",
        ]
        return "\n".join(lines)
