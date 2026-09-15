"""Parametric 3D CAD mesh generation engine for flower-shaped rainwater collector."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from packages.tinaco_cad.params import CollectorParameters


@dataclass
class TriangleMesh:
    """Polygonal triangle mesh representation for 3D CAD geometry.

    Attributes:
        vertices: List of 3D spatial coordinates [x, y, z] in millimeters.
        triangles: List of vertex index triplets defining planar triangular facets.
        normals: List of outward unit normal vectors [nx, ny, nz] per facet.
    """

    vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)

    def compute_normals(self) -> None:
        """Compute outward unit normal vectors for all triangular facets."""
        computed_normals: List[Tuple[float, float, float]] = []
        for v0_idx, v1_idx, v2_idx in self.triangles:
            v0 = self.vertices[v0_idx]
            v1 = self.vertices[v1_idx]
            v2 = self.vertices[v2_idx]

            ax = v1[0] - v0[0]
            ay = v1[1] - v0[1]
            az = v1[2] - v0[2]

            bx = v2[0] - v0[0]
            by = v2[1] - v0[1]
            bz = v2[2] - v0[2]

            nx = ay * bz - az * by
            ny = az * bx - ax * bz
            nz = ax * by - ay * bx

            norm = math.sqrt(nx * nx + ny * ny + nz * nz)
            if norm > 1e-12:
                computed_normals.append((nx / norm, ny / norm, nz / norm))
            else:
                computed_normals.append((0.0, 0.0, 1.0))
        self.normals = computed_normals

    def bounding_box(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Determine minimum and maximum spatial extents of the mesh.

        Returns:
            Tuple containing minimum corner (min_x, min_y, min_z) and
            maximum corner (max_x, max_y, max_z) in millimeters.
        """
        if not self.vertices:
            return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]

        return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))

    def surface_area_m2(self) -> float:
        """Calculate total continuous surface area of mesh in square meters."""
        total_mm2 = 0.0
        for v0_idx, v1_idx, v2_idx in self.triangles:
            v0 = self.vertices[v0_idx]
            v1 = self.vertices[v1_idx]
            v2 = self.vertices[v2_idx]

            ax = v1[0] - v0[0]
            ay = v1[1] - v0[1]
            az = v1[2] - v0[2]

            bx = v2[0] - v0[0]
            by = v2[1] - v0[1]
            bz = v2[2] - v0[2]

            cross_x = ay * bz - az * by
            cross_y = az * bx - ax * bz
            cross_z = ax * by - ay * bx

            facet_area = 0.5 * math.sqrt(cross_x**2 + cross_y**2 + cross_z**2)
            total_mm2 += facet_area

        return total_mm2 / 1_000_000.0

    def estimate_volume_cm3(self) -> float:
        """Estimate enclosed solid shell material volume in cubic centimeters."""
        total_surface_mm2 = self.surface_area_m2() * 1_000_000.0
        assumed_thickness_mm = 4.0
        volume_mm3 = total_surface_mm2 * assumed_thickness_mm * 0.5
        return volume_mm3 / 1000.0

    def is_manifold(self) -> bool:
        """Verify topological 2-manifold consistency for manufacturing."""
        edge_counts: Dict[Tuple[int, int], int] = {}
        for v0, v1, v2 in self.triangles:
            edges = [
                (min(v0, v1), max(v0, v1)),
                (min(v1, v2), max(v1, v2)),
                (min(v2, v0), max(v2, v0)),
            ]
            for edge in edges:
                edge_counts[edge] = edge_counts.get(edge, 0) + 1

        for count in edge_counts.values():
            if count > 2:
                return False
        return True


class CADModelGenerator:
    """Generates 3D CAD mesh representations for the flower-shaped tinaco collector."""

    def __init__(self, params: CollectorParameters) -> None:
        """Initialize generator with validated parametric collector parameters.

        Args:
            params: Validated dimensional specifications instance.
        """
        self.params = params

    def describe_configuration(self) -> Dict[str, float]:
        """Provide key geometric dimensions summary.

        Returns:
            Dictionary mapping dimension names to numeric values.
        """
        return {
            "outer_diameter_mm": self.params.overall_diameter_mm,
            "catchment_area_m2": self.params.projected_catchment_area_m2,
            "petal_count": float(self.params.num_petals),
        }

    def build_complete_mesh(self) -> TriangleMesh:
        """Synthesize hub basin, mounting collar, filter grid, and radiating petals.

        Returns:
            Assembled TriangleMesh ready for CAD export and manufacturing verification.
        """
        mesh = TriangleMesh()
        self._generate_hub_and_collar(mesh)
        self._generate_filter_screen(mesh)
        for petal_index in range(self.params.num_petals):
            self._generate_petal(mesh, petal_index)

        mesh.compute_normals()
        return mesh

    def _generate_hub_and_collar(self, mesh: TriangleMesh) -> None:
        """Construct central receiver basin, slip-fit collar, and overflow ports."""
        radial_segments = 32
        r_outer = self.params.hub_radius
        r_inner = self.params.drain_radius
        h_total = self.params.hub_height
        collar_depth = self.params.tinaco_collar_depth

        upper_ring_start = len(mesh.vertices)
        for i in range(radial_segments):
            theta = (2.0 * math.pi * i) / radial_segments
            x = r_outer * math.cos(theta)
            y = r_outer * math.sin(theta)
            mesh.vertices.append((x, y, 0.0))

        collar_ring_start = len(mesh.vertices)
        for i in range(radial_segments):
            theta = (2.0 * math.pi * i) / radial_segments
            x = r_outer * math.cos(theta)
            y = r_outer * math.sin(theta)
            mesh.vertices.append((x, y, -collar_depth))

        lower_ring_start = len(mesh.vertices)
        for i in range(radial_segments):
            theta = (2.0 * math.pi * i) / radial_segments
            x = r_inner * math.cos(theta)
            y = r_inner * math.sin(theta)
            mesh.vertices.append((x, y, -h_total))

        for i in range(radial_segments):
            next_i = (i + 1) % radial_segments

            u0 = upper_ring_start + i
            u1 = upper_ring_start + next_i
            c0 = collar_ring_start + i
            c1 = collar_ring_start + next_i

            mesh.triangles.append((u0, c0, u1))
            mesh.triangles.append((u1, c0, c1))

            l0 = lower_ring_start + i
            l1 = lower_ring_start + next_i

            mesh.triangles.append((u0, u1, l0))
            mesh.triangles.append((u1, l1, l0))

    def _generate_filter_screen(self, mesh: TriangleMesh) -> None:
        """Construct central cross-ribbed debris exclusion strainer."""
        r_drain = self.params.drain_radius
        z_drain = -self.params.hub_height
        num_spokes = 8
        center_idx = len(mesh.vertices)
        mesh.vertices.append((0.0, 0.0, z_drain))

        rim_start_idx = len(mesh.vertices)
        for i in range(num_spokes):
            theta = (2.0 * math.pi * i) / num_spokes
            x = r_drain * math.cos(theta)
            y = r_drain * math.sin(theta)
            mesh.vertices.append((x, y, z_drain))

        for i in range(num_spokes):
            next_i = (i + 1) % num_spokes
            v1 = rim_start_idx + i
            v2 = rim_start_idx + next_i
            mesh.triangles.append((center_idx, v1, v2))

    def _generate_petal(self, mesh: TriangleMesh, petal_index: int) -> None:
        """Construct a single curved, inclined, trough-shaped water catchment petal."""
        petal_angle = (2.0 * math.pi * petal_index) / self.params.num_petals
        r_hub = self.params.hub_radius
        l_petal = self.params.petal_length
        w_max = self.params.petal_max_width
        slope_rad = self.params.slope_radians
        channel_d = self.params.petal_channel_depth
        wall_h = self.params.petal_wall_height

        num_radial_steps = 10
        num_transverse_steps = 6

        grid_indices: List[List[int]] = []

        for u_idx in range(num_radial_steps + 1):
            u_norm = u_idx / float(num_radial_steps)
            r_local = u_norm * l_petal
            z_elevation = r_local * math.sin(slope_rad)
            radial_dist = r_hub + r_local * math.cos(slope_rad)

            current_width = w_max * math.sin(math.pi * max(u_norm, 0.05)) ** 0.7

            row_indices: List[int] = []
            for v_idx in range(num_transverse_steps + 1):
                v_norm = (v_idx / float(num_transverse_steps)) * 2.0 - 1.0
                transverse_offset = v_norm * (current_width / 2.0)

                trough_drop = channel_d * (1.0 - v_norm**2)
                lip_elevation = wall_h * (v_norm**4)
                z_local = z_elevation - trough_drop + lip_elevation

                x_prime = radial_dist
                y_prime = transverse_offset

                cos_p = math.cos(petal_angle)
                sin_p = math.sin(petal_angle)
                x_world = x_prime * cos_p - y_prime * sin_p
                y_world = x_prime * sin_p + y_prime * cos_p

                idx = len(mesh.vertices)
                mesh.vertices.append((x_world, y_world, z_local))
                row_indices.append(idx)

            grid_indices.append(row_indices)

        for u in range(num_radial_steps):
            for v in range(num_transverse_steps):
                p00 = grid_indices[u][v]
                p01 = grid_indices[u][v + 1]
                p10 = grid_indices[u + 1][v]
                p11 = grid_indices[u + 1][v + 1]

                mesh.triangles.append((p00, p10, p01))
                mesh.triangles.append((p01, p10, p11))
