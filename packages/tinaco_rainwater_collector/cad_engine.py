"""Parametric CAD solid modeling and ISO 10303-21 STEP / STL exporter engine."""

from __future__ import annotations

import datetime
import math
import struct
from typing import List, Tuple

from packages.tinaco_rainwater_collector.models import (
    BillOfMaterials,
    BOMItem,
    Facet3D,
    FlowerCollectorConfig,
    PetalGeometry,
    Point3D,
)


class CADGeometryEngine:
    """Parametric generator for flower collector 3D solid geometry."""

    def __init__(self, config: FlowerCollectorConfig = None) -> None:
        """Initialize CAD geometry engine with parametric specifications."""
        self.config = config or FlowerCollectorConfig()
        validation_errors = self.config.validate()
        if validation_errors:
            raise ValueError(f"Invalid CAD configuration: {'; '.join(validation_errors)}")

    def build_petals(self) -> List[PetalGeometry]:
        """Construct parametric geometric profiles for all individual petals."""
        petals = []
        angle_step = 360.0 / self.config.petal_count
        r_inner = self.config.inner_funnel_diameter_mm / 2.0
        r_outer = self.config.outer_diameter_mm / 2.0
        slope_rad = math.radians(self.config.slope_angle_deg)
        rise = (r_outer - r_inner) * math.tan(slope_rad)

        for i in range(self.config.petal_count):
            start_deg = i * angle_step
            end_deg = (i + 1) * angle_step
            mid_rad = math.radians((start_deg + end_deg) / 2.0)

            apex = Point3D(
                x=r_outer * math.cos(mid_rad),
                y=r_outer * math.sin(mid_rad),
                z=rise,
            )
            throat = Point3D(
                x=r_inner * math.cos(mid_rad),
                y=r_inner * math.sin(mid_rad),
                z=0.0,
            )
            petal = PetalGeometry(
                index=i,
                start_angle_deg=start_deg,
                end_angle_deg=end_deg,
                outer_radius_mm=r_outer,
                inner_radius_mm=r_inner,
                outer_height_mm=rise,
                inner_height_mm=0.0,
                slope_deg=self.config.slope_angle_deg,
                apex_point=apex,
                throat_point=throat,
            )
            petals.append(petal)

        return petals

    def verify_zero_gap_drainage(self) -> Tuple[bool, float, float]:
        """Verify seamless zero-gap junction between petals and central funnel."""
        petals = self.build_petals()
        max_radial_gap = 0.0
        max_vertical_gap = 0.0
        expected_r = self.config.inner_funnel_diameter_mm / 2.0

        for petal in petals:
            throat_r = math.sqrt(petal.throat_point.x**2 + petal.throat_point.y**2)
            radial_diff = abs(throat_r - expected_r)
            vert_diff = abs(petal.throat_point.z - 0.0)
            max_radial_gap = max(max_radial_gap, radial_diff)
            max_vertical_gap = max(max_vertical_gap, vert_diff)

        is_valid = max_radial_gap <= 1e-4 and max_vertical_gap <= 1e-4
        return is_valid, max_radial_gap, max_vertical_gap

    def generate_mesh_facets(self) -> List[Facet3D]:
        """Triangulate outer surfaces for petals, funnel, downspout, and mounting ring."""
        facets = []
        petals = self.build_petals()
        r_inner = self.config.inner_funnel_diameter_mm / 2.0
        r_outer = self.config.outer_diameter_mm / 2.0
        r_drain = self.config.drain_bore_diameter_mm / 2.0
        h_funnel = self.config.funnel_depth_mm

        for petal in petals:
            self._triangulate_petal(petal, r_inner, r_outer, facets)

        self._triangulate_funnel(r_inner, r_drain, h_funnel, facets)
        self._triangulate_downspout(r_drain, h_funnel, facets)
        self._triangulate_adapter_ring(facets)

        return facets

    def _triangulate_petal(
        self,
        petal: PetalGeometry,
        r_inner: float,
        r_outer: float,
        facets: List[Facet3D],
    ) -> None:
        """Subdivide petal sector into planar triangular surface facets."""
        steps = 4
        d_angle = petal.sweep_angle_deg / steps
        slope_rad = math.radians(self.config.slope_angle_deg)
        rise = (r_outer - r_inner) * math.tan(slope_rad)

        for step in range(steps):
            a1_rad = math.radians(petal.start_angle_deg + step * d_angle)
            a2_rad = math.radians(petal.start_angle_deg + (step + 1) * d_angle)

            p_in1 = Point3D(r_inner * math.cos(a1_rad), r_inner * math.sin(a1_rad), 0.0)
            p_in2 = Point3D(r_inner * math.cos(a2_rad), r_inner * math.sin(a2_rad), 0.0)
            p_out1 = Point3D(r_outer * math.cos(a1_rad), r_outer * math.sin(a1_rad), rise)
            p_out2 = Point3D(r_outer * math.cos(a2_rad), r_outer * math.sin(a2_rad), rise)

            edge1 = Point3D(p_out1.x - p_in1.x, p_out1.y - p_in1.y, p_out1.z - p_in1.z)
            edge2 = Point3D(p_in2.x - p_in1.x, p_in2.y - p_in1.y, p_in2.z - p_in1.z)
            normal1 = edge2.cross(edge1).normalized()

            facets.append(Facet3D(normal=normal1, v1=p_in1, v2=p_out1, v3=p_in2))

            edge3 = Point3D(p_out2.x - p_in2.x, p_out2.y - p_in2.y, p_out2.z - p_in2.z)
            edge4 = Point3D(p_out1.x - p_in2.x, p_out1.y - p_in2.y, p_out1.z - p_in2.z)
            normal2 = edge3.cross(edge4).normalized()

            facets.append(Facet3D(normal=normal2, v1=p_in2, v2=p_out1, v3=p_out2))

    def _triangulate_funnel(
        self,
        r_inner: float,
        r_drain: float,
        h_funnel: float,
        facets: List[Facet3D],
    ) -> None:
        """Triangulate conical funnel connecting petals to drain bore."""
        segments = 16
        step_rad = (2.0 * math.pi) / segments

        for i in range(segments):
            a1_rad = i * step_rad
            a2_rad = (i + 1) * step_rad

            top1 = Point3D(r_inner * math.cos(a1_rad), r_inner * math.sin(a1_rad), 0.0)
            top2 = Point3D(r_inner * math.cos(a2_rad), r_inner * math.sin(a2_rad), 0.0)
            bot1 = Point3D(r_drain * math.cos(a1_rad), r_drain * math.sin(a1_rad), -h_funnel)
            bot2 = Point3D(r_drain * math.cos(a2_rad), r_drain * math.sin(a2_rad), -h_funnel)

            edge1 = Point3D(top2.x - top1.x, top2.y - top1.y, top2.z - top1.z)
            edge2 = Point3D(bot1.x - top1.x, bot1.y - top1.y, bot1.z - top1.z)
            n1 = edge1.cross(edge2).normalized()
            facets.append(Facet3D(normal=n1, v1=top1, v2=top2, v3=bot1))

            edge3 = Point3D(bot2.x - bot1.x, bot2.y - bot1.y, bot2.z - bot1.z)
            edge4 = Point3D(top2.x - bot1.x, top2.y - bot1.y, top2.z - bot1.z)
            n2 = edge4.cross(edge3).normalized()
            facets.append(Facet3D(normal=n2, v1=bot1, v2=top2, v3=bot2))

    def _triangulate_downspout(
        self,
        r_drain: float,
        h_funnel: float,
        facets: List[Facet3D],
    ) -> None:
        """Triangulate cylindrical discharge downspout pipe."""
        segments = 16
        step_rad = (2.0 * math.pi) / segments
        z_top = -h_funnel
        z_bot = -h_funnel - 180.0

        for i in range(segments):
            a1_rad = i * step_rad
            a2_rad = (i + 1) * step_rad

            p1 = Point3D(r_drain * math.cos(a1_rad), r_drain * math.sin(a1_rad), z_top)
            p2 = Point3D(r_drain * math.cos(a2_rad), r_drain * math.sin(a2_rad), z_top)
            p3 = Point3D(r_drain * math.cos(a1_rad), r_drain * math.sin(a1_rad), z_bot)
            p4 = Point3D(r_drain * math.cos(a2_rad), r_drain * math.sin(a2_rad), z_bot)

            edge1 = Point3D(p2.x - p1.x, p2.y - p1.y, 0.0)
            edge2 = Point3D(0.0, 0.0, z_bot - z_top)
            n1 = edge1.cross(edge2).normalized()
            facets.append(Facet3D(normal=n1, v1=p1, v2=p2, v3=p3))
            facets.append(Facet3D(normal=n1, v1=p3, v2=p2, v3=p4))

    def _triangulate_adapter_ring(self, facets: List[Facet3D]) -> None:
        """Triangulate tinaco rim mounting adapter flange collar."""
        segments = 16
        step_rad = (2.0 * math.pi) / segments
        r_adapter_in = self.config.tinaco_rim_nominal_mm / 2.0
        r_adapter_out = r_adapter_in + 45.0
        z_flange = -self.config.funnel_depth_mm - 40.0

        for i in range(segments):
            a1_rad = i * step_rad
            a2_rad = (i + 1) * step_rad

            in1 = Point3D(r_adapter_in * math.cos(a1_rad), r_adapter_in * math.sin(a1_rad), z_flange)
            in2 = Point3D(r_adapter_in * math.cos(a2_rad), r_adapter_in * math.sin(a2_rad), z_flange)
            out1 = Point3D(r_adapter_out * math.cos(a1_rad), r_adapter_out * math.sin(a1_rad), z_flange)
            out2 = Point3D(r_adapter_out * math.cos(a2_rad), r_adapter_out * math.sin(a2_rad), z_flange)

            norm = Point3D(0.0, 0.0, 1.0)
            facets.append(Facet3D(normal=norm, v1=in1, v2=out1, v3=in2))
            facets.append(Facet3D(normal=norm, v1=in2, v2=out1, v3=out2))

    def export_stl_ascii(self) -> str:
        """Export 3D model geometry in standard ASCII STL file format."""
        facets = self.generate_mesh_facets()
        lines = ["solid TinacoFlowerCollector"]
        for facet in facets:
            lines.append(facet.to_ascii_stl())
        lines.append("endsolid TinacoFlowerCollector\n")
        return "\n".join(lines)

    def export_stl_binary(self) -> bytes:
        """Export 3D model geometry in standard Binary STL file format."""
        facets = self.generate_mesh_facets()
        header = b"Tinaco Flower Rainwater Collector CAD Model - Antigravity Swarm".ljust(80, b" ")
        body = bytearray(header)
        body.extend(struct.pack("<I", len(facets)))

        for facet in facets:
            body.extend(
                struct.pack(
                    "<12fH",
                    facet.normal.x,
                    facet.normal.y,
                    facet.normal.z,
                    facet.v1.x,
                    facet.v1.y,
                    facet.v1.z,
                    facet.v2.x,
                    facet.v2.y,
                    facet.v2.z,
                    facet.v3.x,
                    facet.v3.y,
                    facet.v3.z,
                    0,
                )
            )

        return bytes(body)

    def export_step_iso10303_21(self) -> str:
        """Export 3D B-Rep model geometry in standard ISO 10303-21 STEP format."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        r_inner = self.config.inner_funnel_diameter_mm / 2.0
        r_outer = self.config.outer_diameter_mm / 2.0
        r_drain = self.config.drain_bore_diameter_mm / 2.0
        slope_rad = math.radians(self.config.slope_angle_deg)
        rise = (r_outer - r_inner) * math.tan(slope_rad)
        h_funnel = self.config.funnel_depth_mm

        file_name_record = (
            f"FILE_NAME('tinaco_flower_collector.step','{timestamp}',"
            "('Engineering Swarm'),('s6pa1rta3n-lab'),'Antigravity CAD v1.0',"
            "'Python 3.14 ISO-10303-21 Generator','');"
        )
        context_record = (
            "#12=(GEOMETRIC_REPRESENTATION_CONTEXT(3) "
            "GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#14)) "
            "GLOBAL_UNIT_ASSIGNED_CONTEXT((#15,#16,#17)) "
            "REPRESENTATION_CONTEXT('3D','solid'));"
        )
        uncertainty_record = (
            "#14=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.0E-4),"
            "#15,'distance_accuracy_value','confusion_accuracy');"
        )

        lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('Parametric Flower Rainwater Collector for Tinaco'),'2;1');",
            file_name_record,
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
            "ENDSEC;",
            "DATA;",
            "#1=APPLICATION_CONTEXT('core data for automotive mechanical design processes');",
            "#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);",
            "#3=PRODUCT_CONTEXT('part definition',#1,'mechanical');",
            "#4=PRODUCT('tinaco_flower_collector','Tinaco Rainwater Collector','3D Solid Model',(#3));",
            "#5=PRODUCT_DEFINITION_FORMATION('1.0','Initial Release',#4);",
            "#6=PRODUCT_DEFINITION('design','Parametric CAD Model',#5,#3);",
            "#7=PRODUCT_DEFINITION_SHAPE('','',#6);",
            "#8=SHAPE_DEFINITION_REPRESENTATION(#7,#9);",
            "#9=ADVANCED_BREP_SHAPE_REPRESENTATION('flower_collector_solid',(#10,#11),#12);",
            "#10=AXIS2_PLACEMENT_3D('origin',#20,#21,#22);",
            "#11=MANIFOLD_SOLID_BREP('collector_body',#13);",
            context_record,
            "#13=CLOSED_SHELL('collector_shell',(#30,#31,#32,#33,#34));",
            uncertainty_record,
            "#15=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));",
            "#16=(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.));",
            "#17=(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT());",
            "#20=CARTESIAN_POINT('',(0.0,0.0,0.0));",
            "#21=DIRECTION('',(0.0,0.0,1.0));",
            "#22=DIRECTION('',(1.0,0.0,0.0));",
            f"#30=CONICAL_SURFACE('central_funnel',#10,{r_inner:.4f},0.4286);",
            f"#31=CYLINDRICAL_SURFACE('drain_downspout',#10,{r_drain:.4f});",
            f"#32=TOROIDAL_SURFACE('outer_collector_lip',#10,{r_outer:.4f},4.0);",
            "#33=PLANE('drain_discharge_plane',#10);",
            "#34=PLANE('petal_top_rim_plane',#10);",
            f"#40=CARTESIAN_POINT('apex_primary',({r_outer:.4f},0.0,{rise:.4f}));",
            f"#41=CARTESIAN_POINT('throat_primary',({r_inner:.4f},0.0,0.0));",
            f"#42=CARTESIAN_POINT('drain_outlet',({r_drain:.4f},0.0,-{h_funnel:.4f}));",
            "#100=ADVANCED_FACE('funnel_face',(#101),#30,.T.);",
            "#101=FACE_OUTER_BOUND('funnel_bound',#102,.T.);",
            "#102=EDGE_LOOP('funnel_loop',(#103,#104));",
            "#103=ORIENTED_EDGE('',*,*,#105,.T.);",
            "#104=ORIENTED_EDGE('',*,*,#106,.T.);",
            "#105=EDGE_CURVE('top_rim',#41,#41,#107,.T.);",
            "#106=EDGE_CURVE('bottom_rim',#42,#42,#108,.T.);",
            f"#107=CIRCLE('funnel_top_circle',#10,{r_inner:.4f});",
            f"#108=CIRCLE('funnel_bottom_circle',#10,{r_drain:.4f});",
            "ENDSEC;",
            "END-ISO-10303-21;\n",
        ]
        return "\n".join(lines)

    def generate_bill_of_materials(self) -> BillOfMaterials:
        """Generate itemized engineering bill of materials for fabrication."""
        items = [
            BOMItem(
                item_number=1,
                part_name="Flower Petal Catchment Segment",
                quantity=self.config.petal_count,
                material=self.config.material_name,
                fabrication_method="Rotomolding / Thermoforming",
                unit_mass_kg=0.485,
                tolerance="ISO 2768-m (+/- 0.8 mm)",
            ),
            BOMItem(
                item_number=2,
                part_name="Central Funnel & Drain Bore Core",
                quantity=1,
                material="Food-Grade Injection-Molded HDPE",
                fabrication_method="High-Pressure Injection Molding",
                unit_mass_kg=0.920,
                tolerance="ISO 2768-f (+/- 0.2 mm)",
            ),
            BOMItem(
                item_number=3,
                part_name="Adjustable Stepped Tinaco Rim Collar",
                quantity=1,
                material="Reinforced UV-Resistant Polypropylene",
                fabrication_method="Rotational Molding / CNC Machining",
                unit_mass_kg=1.150,
                tolerance="ISO 2768-m (+/- 0.5 mm)",
            ),
            BOMItem(
                item_number=4,
                part_name="Quick-Release Retention Clamp Bracket",
                quantity=6,
                material="AISI 304 Stainless Steel",
                fabrication_method="Progressive Die Stamping & Bending",
                unit_mass_kg=0.085,
                tolerance="DIN 6930-m (+/- 0.3 mm)",
            ),
            BOMItem(
                item_number=5,
                part_name="Clamp Fastener Bolt M8x45 & Wing Nut",
                quantity=6,
                material="AISI 316 Marine-Grade Stainless Steel",
                fabrication_method="Cold Forging & Thread Rolling",
                unit_mass_kg=0.035,
                tolerance="ISO 4762 6g/6H",
            ),
            BOMItem(
                item_number=6,
                part_name="Conical Mesh Debris Pre-Filter (1.2mm)",
                quantity=1,
                material="AISI 304 Stainless Steel Wire Mesh",
                fabrication_method="Woven Mesh Die Cutting & Seam Welding",
                unit_mass_kg=0.140,
                tolerance="ISO 9044 Grade 1",
            ),
            BOMItem(
                item_number=7,
                part_name="Perimeter Rim Sanitary Seal Gasket",
                quantity=1,
                material="EPDM Closed-Cell Elastomer (Food-Grade)",
                fabrication_method="Continuous Extrusion & Vulcanized Joint",
                unit_mass_kg=0.310,
                tolerance="DIN 7715 E2 (+/- 0.5 mm)",
            ),
        ]
        return BillOfMaterials(items=items)
