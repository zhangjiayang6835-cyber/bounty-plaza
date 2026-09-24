"""Engineering orthographic drawings and technical blueprint generator."""

from __future__ import annotations

import math
from typing import List

from packages.tinaco_rainwater_collector.models import FlowerCollectorConfig


class EngineeringDrawingGenerator:
    """Renderer for manufacturing vector graphics and terminal schematics."""

    def __init__(self, config: FlowerCollectorConfig = None) -> None:
        """Initialize drawing generator with collector geometry configuration."""
        self.config = config or FlowerCollectorConfig()

    def generate_svg_drawing(self) -> str:
        """Generate production SVG drawing with orthographic views and title block."""
        width = 1200
        height = 850

        plan_cx = 360
        plan_cy = 380
        plan_scale = 0.22

        r_out_px = (self.config.outer_diameter_mm / 2.0) * plan_scale
        r_fun_px = (self.config.inner_funnel_diameter_mm / 2.0) * plan_scale
        r_drn_px = (self.config.drain_bore_diameter_mm / 2.0) * plan_scale

        petal_svg_elements = self._render_svg_petals(plan_cx, plan_cy, r_out_px, r_fun_px)
        clamps_svg_elements = self._render_svg_clamps(plan_cx, plan_cy, r_fun_px + 25.0)

        elevation_svg = self._render_svg_elevation(cx=880, base_y=420, scale=0.32)
        title_block_svg = self._render_svg_title_block(width=width, height=height)

        svg_content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'width="100%" height="100%" style="background-color: #0b1120; font-family: monospace;">',
            '<defs>',
            '  <style>',
            '    .dim-line { stroke: #38bdf8; stroke-width: 1.5; stroke-dasharray: 4,4; }',
            '    .dim-text { fill: #38bdf8; font-size: 13px; font-weight: bold; }',
            '    .body-line { stroke: #34d399; stroke-width: 2.2; fill: none; }',
            '    .petal-fill { fill: #064e3b; fill-opacity: 0.45; stroke: #10b981; stroke-width: 1.8; }',
            '    .core-fill { fill: #1e3a8a; fill-opacity: 0.55; stroke: #60a5fa; stroke-width: 2.0; }',
            '    .section-fill { fill: #312e81; fill-opacity: 0.4; stroke: #a78bfa; stroke-width: 2.0; }',
            '    .title-text { fill: #f8fafc; font-size: 16px; font-weight: bold; }',
            '    .sub-text { fill: #94a3b8; font-size: 12px; }',
            '  </style>',
            '</defs>',
            f'<rect x="15" y="15" width="{width - 30}" height="{height - 30}" '
            'fill="none" stroke="#475569" stroke-width="2"/>',
            f'<rect x="25" y="25" width="{width - 50}" height="{height - 50}" '
            'fill="none" stroke="#334155" stroke-width="1"/>',
            '<text x="50" y="65" class="title-text">VIEW A: TOP (PLAN) VIEW - CATCHMENT PETALS & CORE</text>',
            petal_svg_elements,
            f'<circle cx="{plan_cx}" cy="{plan_cy}" r="{r_out_px:.1f}" '
            'fill="none" stroke="#38bdf8" stroke-width="2"/>',
            f'<circle cx="{plan_cx}" cy="{plan_cy}" r="{r_fun_px:.1f}" class="core-fill"/>',
            f'<circle cx="{plan_cx}" cy="{plan_cy}" r="{r_drn_px:.1f}" '
            'fill="#0284c7" stroke="#e0f2fe" stroke-width="1.8"/>',
            clamps_svg_elements,
            f'<line x1="{plan_cx - r_out_px - 40}" y1="{plan_cy + r_out_px + 30}" '
            f'x2="{plan_cx + r_out_px + 40}" y2="{plan_cy + r_out_px + 30}" class="dim-line"/>',
            f'<text x="{plan_cx - 85}" y="{plan_cy + r_out_px + 50}" class="dim-text">'
            f'DIAMETER = {self.config.outer_diameter_mm:.0f} mm</text>',
            '<text x="680" y="65" class="title-text">VIEW B: SECTION A-A ELEVATION & TINACO ADAPTER</text>',
            elevation_svg,
            title_block_svg,
            '</svg>',
        ]
        return "\n".join(svg_content)

    def _render_svg_petals(self, cx: float, cy: float, r_out: float, r_in: float) -> str:
        """Render polar array of curved flower petals in SVG format."""
        elements: List[str] = []
        count = self.config.petal_count
        step_rad = (2.0 * math.pi) / count

        for i in range(count):
            a_start = i * step_rad
            a_end = (i + 1) * step_rad
            a_mid = (a_start + a_end) / 2.0

            x_in1 = cx + r_in * math.cos(a_start)
            y_in1 = cy + r_in * math.sin(a_start)
            x_in2 = cx + r_in * math.cos(a_end)
            y_in2 = cy + r_in * math.sin(a_end)

            x_out1 = cx + r_out * math.cos(a_start)
            y_out1 = cy + r_out * math.sin(a_start)
            x_out2 = cx + r_out * math.cos(a_end)
            y_out2 = cy + r_out * math.sin(a_end)

            ctrl_r = r_out * 1.08
            x_ctrl = cx + ctrl_r * math.cos(a_mid)
            y_ctrl = cy + ctrl_r * math.sin(a_mid)

            path_data = (
                f"M {x_in1:.1f} {y_in1:.1f} "
                f"L {x_out1:.1f} {y_out1:.1f} "
                f"Q {x_ctrl:.1f} {y_ctrl:.1f} {x_out2:.1f} {y_out2:.1f} "
                f"L {x_in2:.1f} {y_in2:.1f} Z"
            )
            elements.append(f'<path d="{path_data}" class="petal-fill"/>')

        return "\n".join(elements)

    def _render_svg_clamps(self, cx: float, cy: float, r_clamp: float) -> str:
        """Render positions of adjustable rim retention clamp brackets."""
        elements: List[str] = []
        count = 6
        step_rad = (2.0 * math.pi) / count
        for i in range(count):
            angle = i * step_rad
            x = cx + r_clamp * math.cos(angle)
            y = cy + r_clamp * math.sin(angle)
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#f59e0b" stroke="#fef3c7" stroke-width="1.5"/>'
            )
        return "\n".join(elements)

    def _render_svg_elevation(self, cx: float, base_y: float, scale: float) -> str:
        """Render elevation cross-section showing inward slope and stepped adapter."""
        half_w = (self.config.outer_diameter_mm / 2.0) * scale
        funnel_w = (self.config.inner_funnel_diameter_mm / 2.0) * scale
        drain_w = (self.config.drain_bore_diameter_mm / 2.0) * scale
        rim_w = (self.config.tinaco_rim_nominal_mm / 2.0) * scale

        slope_rad = math.radians(self.config.slope_angle_deg)
        rise = ((self.config.outer_diameter_mm - self.config.inner_funnel_diameter_mm) / 2.0) * math.tan(
            slope_rad
        ) * scale
        funnel_h = self.config.funnel_depth_mm * scale
        spout_h = 180.0 * scale

        y_top = base_y - rise
        y_drain = base_y + funnel_h
        y_bot = y_drain + spout_h

        left_rim_x = cx - half_w
        right_rim_x = cx + half_w
        left_funnel_x = cx - funnel_w
        right_funnel_x = cx + funnel_w
        left_drain_x = cx - drain_w
        right_drain_x = cx + drain_w

        profile_path = (
            f"M {left_rim_x:.1f} {y_top:.1f} "
            f"L {left_funnel_x:.1f} {base_y:.1f} "
            f"L {left_drain_x:.1f} {y_drain:.1f} "
            f"L {left_drain_x:.1f} {y_bot:.1f} "
            f"L {right_drain_x:.1f} {y_bot:.1f} "
            f"L {right_drain_x:.1f} {y_drain:.1f} "
            f"L {right_funnel_x:.1f} {base_y:.1f} "
            f"L {right_rim_x:.1f} {y_top:.1f}"
        )

        elements = [
            f'<path d="{profile_path}" class="body-line"/>',
            f'<rect x="{cx - rim_w - 18:.1f}" y="{base_y + 15:.1f}" '
            'width="36" height="50" fill="#f59e0b" fill-opacity="0.6" stroke="#fbbf24" stroke-width="1.5"/>',
            f'<rect x="{cx + rim_w - 18:.1f}" y="{base_y + 15:.1f}" '
            'width="36" height="50" fill="#f59e0b" fill-opacity="0.6" stroke="#fbbf24" stroke-width="1.5"/>',
            f'<line x1="{cx - rim_w:.1f}" y1="{base_y + 65:.1f}" '
            f'x2="{cx + rim_w:.1f}" y2="{base_y + 65:.1f}" class="dim-line"/>',
            f'<text x="{cx - 100}" y="{base_y + 85}" class="dim-text">'
            f'TINACO RIM = {self.config.tinaco_rim_nominal_mm:.0f} mm</text>',
            f'<text x="{cx + funnel_w + 15}" y="{base_y - (rise / 2.0)}" class="dim-text">'
            f'SLOPE = {self.config.slope_angle_deg:.1f} DEG</text>',
        ]
        return "\n".join(elements)

    def _render_svg_title_block(self, width: int, height: int) -> str:
        """Render manufacturing title block with standard tolerances and metadata."""
        tb_x = width - 480
        tb_y = height - 140
        tb_w = 445
        tb_h = 105

        lines = [
            f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" '
            'fill="#1e293b" stroke="#64748b" stroke-width="1.8"/>',
            f'<line x1="{tb_x}" y1="{tb_y + 35}" x2="{tb_x + tb_w}" y2="{tb_y + 35}" '
            'stroke="#475569" stroke-width="1"/>',
            f'<line x1="{tb_x}" y1="{tb_y + 70}" x2="{tb_x + tb_w}" y2="{tb_y + 70}" '
            'stroke="#475569" stroke-width="1"/>',
            f'<line x1="{tb_x + 220}" y1="{tb_y}" x2="{tb_x + 220}" y2="{tb_y + tb_h}" '
            'stroke="#475569" stroke-width="1"/>',
            f'<text x="{tb_x + 10}" y="{tb_y + 24}" class="title-text">TINACO RAINWATER COLLECTOR</text>',
            f'<text x="{tb_x + 10}" y="{tb_y + 55}" class="sub-text">DOC: CAD-TNC-FLW-1633</text>',
            f'<text x="{tb_x + 10}" y="{tb_y + 92}" class="sub-text">ORGANIZATION: s6pa1rta3n-lab</text>',
            f'<text x="{tb_x + 230}" y="{tb_y + 24}" class="sub-text">SCALE: 1:10 | REV: 1.0</text>',
            f'<text x="{tb_x + 230}" y="{tb_y + 55}" class="sub-text">TOLERANCE: ISO 2768-m</text>',
            f'<text x="{tb_x + 230}" y="{tb_y + 92}" class="sub-text">MATERIAL: FOOD-GRADE HDPE</text>',
        ]
        return "\n".join(lines)

    def generate_ascii_blueprint(self) -> str:
        """Generate formatted ASCII diagram for terminal inspection."""
        deg = self.config.slope_angle_deg
        od_mm = self.config.outer_diameter_mm
        fn_mm = self.config.inner_funnel_diameter_mm
        dr_mm = self.config.drain_bore_diameter_mm
        rm_mm = self.config.tinaco_rim_nominal_mm
        r_min = self.config.tinaco_rim_min_mm
        r_max = self.config.tinaco_rim_max_mm

        lines = [
            "=" * 80,
            "      PARAMETRIC FLOWER-SHAPED RAINWATER COLLECTOR FOR TINACO - REV 1.0         ",
            "=" * 80,
            "                 \\                                            /                 ",
            f"                  \\   <- SLOPE: {deg:.1f} DEG (GRAVITY DRAINAGE) ->   /                  ",
            "                   \\                                        /                   ",
              "  OUTER RIM:        \\________________                      /       OUTER RIM:   ",
            f"  OD = {od_mm:.0f} mm          \\              /                    OD = {od_mm:.0f} mm",
              "                      \\  FUNNEL:     /                                          ",
            f"                       \\ OD = {fn_mm:.0f} mm /                                          ",
            "                        |          |                                            ",
            "     [CLAMP BRACKET] ===|  DRAIN   |=== [CLAMP BRACKET]                         ",
            f"     ADAPTER COLLAR:    |  BORE    |    TINACO TANK RIM: {rm_mm:.0f} mm             ",
            f"     FIT: {r_min:.0f}-{r_max:.0f} mm      |  {dr_mm:.0f} mm  |    (EPDM SANITARY SEAL GASKET)  ",
            "                        |          |                                            ",
            "                        |          |    CENTRAL DOWNSPOUT TUBE                  ",
            "                        |    ||    |    (FEEDS INTO TINACO NECK)                ",
            "                        \\____||____/                                            ",
            "                             \\/                                                 ",
            "-" * 80,
            (
                f" SPECIFICATIONS: {self.config.petal_count} Petals | "
                f"Catchment: {self.config.catchment_area_m2:.2f} m2 | "
                f"HDPE Density: {self.config.material_density_g_cm3} g/cm3"
            ),
            "=" * 80,
        ]
        return "\n".join(lines)
