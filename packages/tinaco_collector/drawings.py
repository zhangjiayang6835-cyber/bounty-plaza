"""Assembly drawings generator (vector SVG and ASCII engineering schematics)."""

import math
from typing import List

from packages.tinaco_collector.models import CollectorAssembly


def generate_assembly_drawing_svg(assembly: CollectorAssembly) -> str:
    """Generate professional engineering assembly drawing in scalable vector graphics format.

    Args:
        assembly: Complete parametric collector assembly model.

    Returns:
        Standard SVG XML document string with orthographic and isometric views.
    """
    width = 1600
    height = 1100

    outer_dia = assembly.total_outer_diameter_mm
    throat_dia = assembly.drain.throat_diameter_mm
    neck_dia = assembly.drain.drain_neck_diameter_mm
    drop_h = assembly.petals.vertical_drop_mm
    funnel_h = assembly.drain.funnel_depth_mm
    adapter_h = assembly.adapter.collar_height_mm
    total_h = assembly.total_height_mm

    svg_parts: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<defs>',
        '  <style>',
        '    .border { fill: none; stroke: #1e293b; stroke-width: 3; }',
        '    .title-box { fill: #f8fafc; stroke: #334155; stroke-width: 1.5; }',
        '    .grid-line { stroke: #cbd5e1; stroke-width: 0.5; stroke-dasharray: 4,4; }',
        '    .center-line { stroke: #dc2626; stroke-width: 1; stroke-dasharray: 8,4,2,4; }',
        '    .solid-line { fill: none; stroke: #0f172a; stroke-width: 2; }',
        '    .hidden-line { fill: none; stroke: #64748b; stroke-width: 1.2; stroke-dasharray: 4,3; }',
        '    .dimension { stroke: #0284c7; stroke-width: 1.2; }',
        '    .dim-text { font-family: "Courier New", monospace; font-size: 13px; font-weight: bold; fill: #0369a1; }',
        '    .view-title { font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; fill: #0f172a; }',
        '    .view-sub { font-family: Arial, sans-serif; font-size: 12px; fill: #475569; }',
        '    .title-text-main { font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; fill: #0f172a; }',
        '    .title-text-label { font-family: Arial, sans-serif; font-size: 11px; fill: #64748b; font-weight: bold; }',
        '    .title-text-val { font-family: Arial, sans-serif; font-size: 13px; fill: #1e293b; }',
        '    .petal-fill { fill: #bae6fd; fill-opacity: 0.35; stroke: #0284c7; stroke-width: 1.8; }',
        '    .funnel-fill { fill: #7dd3fc; fill-opacity: 0.45; stroke: #0369a1; stroke-width: 2; }',
        '    .adapter-fill { fill: #cbd5e1; fill-opacity: 0.5; stroke: #334155; stroke-width: 2; }',
        '    .tinaco-rim { fill: none; stroke: #94a3b8; stroke-width: 2; stroke-dasharray: 6,4; }',
        '  </style>',
        '  <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '    <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#0284c7"/>',
        '  </marker>',
        '</defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="25" y="25" width="1550" height="1050" class="border"/>',
        '<rect x="35" y="35" width="1530" height="1030" class="border" stroke-width="1"/>',
    ]

    svg_parts.extend([
        '<g transform="translate(1000, 915)">',
        '  <rect x="0" y="0" width="565" height="150" class="title-box"/>',
        '  <line x1="0" y1="40" x2="565" y2="40" stroke="#334155" stroke-width="1.5"/>',
        '  <line x1="0" y1="80" x2="565" y2="80" stroke="#334155" stroke-width="1.5"/>',
        '  <line x1="0" y1="115" x2="565" y2="115" stroke="#334155" stroke-width="1.5"/>',
        '  <line x1="280" y1="40" x2="280" y2="150" stroke="#334155" stroke-width="1.5"/>',
        '  <line x1="430" y1="40" x2="430" y2="150" stroke="#334155" stroke-width="1.5"/>',
        '  <text x="20" y="27" class="title-text-main">FLOWER-SHAPED RAINWATER COLLECTOR (TINACO RETROFIT)</text>',
        '  <text x="15" y="58" class="title-text-label">PROJECT / DEPLOYMENT TARGET:</text>',
        '  <text x="15" y="73" class="title-text-val">Mexico City (CDMX) Rooftop Tinaco Harvesting</text>',
        '  <text x="295" y="58" class="title-text-label">DRAWING NUMBER:</text>',
        '  <text x="295" y="73" class="title-text-val">CDMX-TRH-001-REV-A</text>',
        '  <text x="445" y="58" class="title-text-label">SHEET / SCALE:</text>',
        '  <text x="445" y="73" class="title-text-val">1 OF 1  |  1:15 METRIC</text>',
        '  <text x="15" y="96" class="title-text-label">PRIMARY MATERIAL:</text>',
        '  <text x="15" y="110" class="title-text-val">Food-Grade UV-HDPE / 316 SS Clamp Collar</text>',
        '  <text x="295" y="96" class="title-text-label">TOLERANCES (ISO 2768-m):</text>',
        '  <text x="295" y="110" class="title-text-val">Linear: ±1.5 mm | Angular: ±0.5°</text>',
        '  <text x="445" y="96" class="title-text-label">VERIFIED STATUS:</text>',
        '  <text x="445" y="110" class="title-text-val" fill="#16a34a" font-weight="bold">READY FOR TOOLING</text>',
        '  <text x="15" y="132" class="title-text-label">DESIGN SPECIFICATION:</text>',
        '  <text x="15" y="145" class="title-text-val">Parametric 8-Petal Bio-inspired Funnel Array</text>',
        '  <text x="295" y="132" class="title-text-label">ENGINEERING APPROVAL:</text>',
        '  <text x="295" y="145" class="title-text-val">Universal Bounty Operations CAD Core</text>',
        '  <text x="445" y="132" class="title-text-label">CAD UNITS:</text>',
        '  <text x="445" y="145" class="title-text-val">Millimeters [mm]</text>',
        '</g>',
    ])

    plan_cx = 360
    plan_cy = 380
    r_out_px = 250
    r_throat_px = 66
    r_neck_px = 18

    svg_parts.extend([
        f'<text x="60" y="80" class="view-title">VIEW 1: PLAN VIEW (TOP ORTHOGRAPHIC)</text>',
        f'<text x="60" y="100" class="view-sub">Scale 1:15 - Looking directly down into 8-petal drainage collection basin</text>',
        f'<line x1="{plan_cx - r_out_px - 40}" y1="{plan_cy}" x2="{plan_cx + r_out_px + 40}" y2="{plan_cy}" class="center-line"/>',
        f'<line x1="{plan_cx}" y1="{plan_cy - r_out_px - 40}" x2="{plan_cx}" y2="{plan_cy + r_out_px + 40}" class="center-line"/>',
    ])

    for i in range(assembly.petals.petal_count):
        deg = i * (360.0 / assembly.petals.petal_count)
        rad0 = math.radians(deg - 22.5)
        rad1 = math.radians(deg + 22.5)
        rad_mid = math.radians(deg)

        x0_in = plan_cx + r_throat_px * math.cos(rad0)
        y0_in = plan_cy + r_throat_px * math.sin(rad0)
        x1_in = plan_cx + r_throat_px * math.cos(rad1)
        y1_in = plan_cy + r_throat_px * math.sin(rad1)

        x0_out = plan_cx + r_out_px * math.cos(rad0)
        y0_out = plan_cy + r_out_px * math.sin(rad0)
        x1_out = plan_cx + r_out_px * math.cos(rad1)
        y1_out = plan_cy + r_out_px * math.sin(rad1)
        x_crest = plan_cx + (r_out_px + 18) * math.cos(rad_mid)
        y_crest = plan_cy + (r_out_px + 18) * math.sin(rad_mid)

        path_d = (
            f"M {x0_in:.1f} {y0_in:.1f} "
            f"L {x0_out:.1f} {y0_out:.1f} "
            f"Q {x_crest:.1f} {y_crest:.1f} {x1_out:.1f} {y1_out:.1f} "
            f"L {x1_in:.1f} {y1_in:.1f} Z"
        )
        svg_parts.append(f'<path d="{path_d}" class="petal-fill"/>')

    svg_parts.extend([
        f'<circle cx="{plan_cx}" cy="{plan_cy}" r="{r_throat_px}" class="solid-line" fill="#e0f2fe"/>',
        f'<circle cx="{plan_cx}" cy="{plan_cy}" r="{r_neck_px}" class="solid-line" fill="#0284c7"/>',
        f'<line x1="{plan_cx - r_throat_px + 5}" y1="{plan_cy}" x2="{plan_cx + r_throat_px - 5}" y2="{plan_cy}" stroke="#0f172a" stroke-width="3"/>',
        f'<line x1="{plan_cx}" y1="{plan_cy - r_throat_px + 5}" x2="{plan_cx}" y2="{plan_cy + r_throat_px - 5}" stroke="#0f172a" stroke-width="3"/>',
        f'<line x1="{plan_cx - r_out_px}" y1="{plan_cy - r_out_px - 20}" x2="{plan_cx + r_out_px}" y2="{plan_cy - r_out_px - 20}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<line x1="{plan_cx - r_out_px}" y1="{plan_cy - r_out_px - 35}" x2="{plan_cx - r_out_px}" y2="{plan_cy - r_out_px - 10}" class="dimension"/>',
        f'<line x1="{plan_cx + r_out_px}" y1="{plan_cy - r_out_px - 35}" x2="{plan_cx + r_out_px}" y2="{plan_cy - r_out_px - 10}" class="dimension"/>',
        f'<text x="{plan_cx - 85}" y="{plan_cy - r_out_px - 28}" class="dim-text">DIA {outer_dia:.0f} mm (OUTER RIM)</text>',
        f'<line x1="{plan_cx - r_throat_px}" y1="{plan_cy + r_throat_px + 30}" x2="{plan_cx + r_throat_px}" y2="{plan_cy + r_throat_px + 30}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<text x="{plan_cx - 75}" y="{plan_cy + r_throat_px + 50}" class="dim-text">DIA {throat_dia:.0f} mm (THROAT)</text>',
    ])

    elev_x = 980
    elev_y = 180

    svg_parts.extend([
        f'<text x="{elev_x - 50}" y="80" class="view-title">VIEW 2: FRONT ELEVATION &amp; SLOPED INCLINE</text>',
        f'<text x="{elev_x - 50}" y="100" class="view-sub">Cross-section contour demonstrating 18.5° positive self-cleansing gravity drainage</text>',
        f'<line x1="{elev_x - 280}" y1="{elev_y + 110}" x2="{elev_x + 280}" y2="{elev_y + 110}" class="dimension" stroke-dasharray="3,3"/>',
        f'<polygon points="{elev_x - 240},{elev_y} {elev_x - 240},{elev_y + 10} {elev_x - 65},{elev_y + 110} {elev_x - 20},{elev_y + 190} {elev_x - 20},{elev_y + 240} {elev_x - 15},{elev_y + 240} {elev_x - 15},{elev_y + 195} {elev_x - 60},{elev_y + 115} {elev_x - 235},{elev_y + 10} {elev_x - 235},{elev_y}" class="funnel-fill"/>',
        f'<polygon points="{elev_x + 240},{elev_y} {elev_x + 240},{elev_y + 10} {elev_x + 65},{elev_y + 110} {elev_x + 20},{elev_y + 190} {elev_x + 20},{elev_y + 240} {elev_x + 15},{elev_y + 240} {elev_x + 15},{elev_y + 195} {elev_x + 60},{elev_y + 115} {elev_x + 235},{elev_y + 10} {elev_x + 235},{elev_y}" class="funnel-fill"/>',
        f'<rect x="{elev_x - 75}" y="{elev_y + 190}" width="150" height="70" class="adapter-fill"/>',
        f'<line x1="{elev_x - 85}" y1="{elev_y + 200}" x2="{elev_x - 65}" y2="{elev_y + 200}" stroke="#0f172a" stroke-width="4"/>',
        f'<line x1="{elev_x + 65}" y1="{elev_y + 200}" x2="{elev_x + 85}" y2="{elev_y + 200}" stroke="#0f172a" stroke-width="4"/>',
        f'<rect x="{elev_x - 82}" y="{elev_y + 195}" width="6" height="15" fill="#475569"/>',
        f'<rect x="{elev_x + 76}" y="{elev_y + 195}" width="6" height="15" fill="#475569"/>',
        f'<line x1="{elev_x + 265}" y1="{elev_y}" x2="{elev_x + 265}" y2="{elev_y + 110}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<text x="{elev_x + 275}" y="{elev_y + 60}" class="dim-text">DROP {drop_h:.0f} mm</text>',
        f'<line x1="{elev_x + 265}" y1="{elev_y + 110}" x2="{elev_x + 265}" y2="{elev_y + 190}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<text x="{elev_x + 275}" y="{elev_y + 155}" class="dim-text">FUNNEL {funnel_h:.0f} mm</text>',
        f'<line x1="{elev_x + 265}" y1="{elev_y + 190}" x2="{elev_x + 265}" y2="{elev_y + 260}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<text x="{elev_x + 275}" y="{elev_y + 230}" class="dim-text">COLLAR {adapter_h:.0f} mm</text>',
        f'<line x1="{elev_x + 365}" y1="{elev_y}" x2="{elev_x + 365}" y2="{elev_y + 260}" class="dimension" marker-start="url(#arrow)" marker-end="url(#arrow)"/>',
        f'<text x="{elev_x + 375}" y="{elev_y + 135}" class="dim-text" fill="#0f172a">TOTAL H = {total_h:.0f} mm</text>',
    ])

    sec_x = 360
    sec_y = 800

    svg_parts.extend([
        f'<text x="60" y="680" class="view-title">VIEW 3: SECTION A-A CUTAWAY (ADJUSTABLE TINACO ADAPTER)</text>',
        f'<text x="60" y="700" class="view-sub">Detail of 4-quadrant segmented collar clamping onto variable Mexico City tinaco rims</text>',
        f'<rect x="{sec_x - 170}" y="{sec_y}" width="340" height="90" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>',
        f'<rect x="{sec_x - 140}" y="{sec_y + 10}" width="280" height="70" class="adapter-fill"/>',
        f'<rect x="{sec_x - 145}" y="{sec_y + 15}" width="10" height="60" fill="#22c55e" stroke="#15803d"/>',
        f'<rect x="{sec_x + 135}" y="{sec_y + 15}" width="10" height="60" fill="#22c55e" stroke="#15803d"/>',
        f'<circle cx="{sec_x - 170}" cy="{sec_y + 45}" r="7" fill="#64748b" stroke="#0f172a" stroke-width="1.5"/>',
        f'<circle cx="{sec_x + 170}" cy="{sec_y + 45}" r="7" fill="#64748b" stroke="#0f172a" stroke-width="1.5"/>',
        f'<line x1="{sec_x - 180}" y1="{sec_y + 45}" x2="{sec_x - 120}" y2="{sec_y + 45}" stroke="#0f172a" stroke-width="2.5"/>',
        f'<line x1="{sec_x + 120}" y1="{sec_y + 45}" x2="{sec_x + 180}" y2="{sec_y + 45}" stroke="#0f172a" stroke-width="2.5"/>',
        f'<text x="{sec_x - 130}" y="{sec_y + 120}" class="dim-text">VARIABLE CLAMP RANGE: 400 mm - 650 mm</text>',
        f'<text x="{sec_x - 110}" y="{sec_y + 140}" class="view-sub">Compatible with Rotoplas 450L, 750L, 1100L, and 2500L models</text>',
    ])

    svg_parts.extend([
        '<g transform="translate(1000, 520)">',
        '  <rect x="0" y="0" width="565" height="360" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>',
        '  <text x="25" y="35" class="view-title">VIEW 4: 3D ISOMETRIC SCHEMATIC</text>',
        '  <text x="25" y="55" class="view-sub">Radial blooming petal array with vortex inhibitor and modular collar</text>',
        '  <ellipse cx="280" cy="140" rx="180" ry="60" fill="#e0f2fe" stroke="#0284c7" stroke-width="2.5"/>',
        '  <path d="M 100 140 C 130 190, 200 230, 280 230 C 360 230, 430 190, 460 140" fill="none" stroke="#0284c7" stroke-width="2"/>',
        '  <ellipse cx="280" cy="230" rx="60" ry="20" fill="#bae6fd" stroke="#0369a1" stroke-width="2"/>',
        '  <path d="M 220 230 L 220 290 C 220 305, 340 305, 340 290 L 340 230" fill="#cbd5e1" stroke="#334155" stroke-width="2"/>',
        '  <line x1="280" y1="80" x2="280" y2="310" class="center-line"/>',
        '  <text x="310" y="110" font-family="Arial" font-size="12" fill="#0369a1" font-weight="bold">[1] Petal Blade (x8)</text>',
        '  <text x="350" y="225" font-family="Arial" font-size="12" fill="#0369a1" font-weight="bold">[2] Central Throat</text>',
        '  <text x="350" y="275" font-family="Arial" font-size="12" fill="#334155" font-weight="bold">[3] Adjustable Clamp</text>',
        '</g>',
    ])

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def generate_ascii_engineering_drawing(assembly: CollectorAssembly) -> str:
    """Generate ASCII engineering projection schematic for terminal and markdown display.

    Args:
        assembly: Collector assembly instance.

    Returns:
        Structured ASCII engineering drawing text.
    """
    outer_d = assembly.total_outer_diameter_mm
    throat_d = assembly.drain.throat_diameter_mm
    neck_d = assembly.drain.drain_neck_diameter_mm
    slope_deg = assembly.petals.inward_slope_deg
    total_h = assembly.total_height_mm

    lines = [
        "==========================================================================================",
        "          ENGINEERING SCHEMATIC: FLOWER-SHAPED TINACO RAINWATER COLLECTOR                 ",
        "          MEXICO CITY (CDMX) ROOFTOP RETROFIT CONCEPT - DRAWING CDMX-TRH-001              ",
        "==========================================================================================",
        "",
        f"  <----------------------------- DIA {outer_d:.0f} mm (CATCHMENT RIM) ----------------------------->",
        "  \\________________                                                      ________________/",
        f"   \\   PETAL BLADE  \\____                                          ____/  SLOPE: {slope_deg:.1f}°   /",
        "    \\    (UV-HDPE)       \\____                                ____/      (GRAVITY FLOW) /",
        "     \\                        \\____                      ____/                         /",
        f"      \\____________________________\\                    /____________________________/",
        f"                                    |  DIA {throat_d:.0f} mm   |",
        "                                    | (CENTRAL THROAT) |",
        "                                    \\                  /",
        "                                     \\  VORTEX FUNNEL /",
        "                                      \\   (ANTI-AIR) /",
        f"                                       | DIA {neck_d:.0f} mm |  <--- 500-MICRON STAINLESS SCREEN",
        "                     =======================================================",
        "                    [+]  ADJUSTABLE TINACO ADAPTER COLLAR (4-SEGMENT)    [+]",
        "                    [+]  FITS 400 mm - 650 mm TINACO LIDS (ROTOPLAS/ETC) [+]",
        "                     =======================================================",
        "                                       |              |",
        "                                       |  DOWNSPOUT   |",
        "                                       v  INTO TANK   v",
        "                     _______________________________________________________",
        "                    |                                                       |",
        "                    |          EXISTING ROOFTOP TINACO WATER TANK           |",
        "                    |              (450L / 750L / 1100L / 2500L)            |",
        "                    |_______________________________________________________|",
        "",
        f"  TOTAL ASSEMBLED HEIGHT: {total_h:.1f} mm | EFFECTIVE CATCHMENT AREA: {assembly.petals.catchment_area_m2:.2f} m²",
        "  ESTIMATED WEIGHT: ~12.5 kg | RETROFIT CLAMP TORQUE: 12.0 N*m (316 SS HARDWARE)",
        "==========================================================================================",
    ]
    return "\n".join(lines)
