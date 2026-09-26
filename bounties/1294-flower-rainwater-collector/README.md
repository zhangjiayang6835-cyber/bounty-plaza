# Flower-shaped rainwater collector for a tinaco

Parametric CAD concept for mirror issue #1294 / upstream issue #1365. The collector uses eight raised outer petals to shed water inward into a central screened funnel, then through a tunable slip-fit/clamped outlet collar intended to retrofit to a measured tinaco opening.

This is a **concept**, not a field-verified potable-water or structural design. Measure the actual tank before fabrication and verify wind/roof loads, material compatibility, filtration, overflow, first-flush handling and local plumbing requirements for the intended installation.

## Files

- `flower_rainwater_collector.scad` — editable source of truth for the collector, funnel, integral debris screen and outlet collar.
- `generate_drawing.py` — creates a compact dimensioned SVG assembly schematic from the SCAD parameter table.
- `export_step.py` — imports the rendered STL with OpenCascade, sews it, requires one valid solid, writes STEP, then re-imports the STEP as a validity check.
- `verify_assets.py` — checks the actual generated mesh for closed/manifold edges, one connected body, positive volume, expected envelope, an unobstructed central flow path, a solid outlet-wall control probe, and one valid STEP solid.
- `requirements-cad.txt` — pins the OpenCascade Python binding used for STEP conversion and validation.

## Default concept dimensions

| Parameter | Default |
| --- | ---: |
| Petals | 8 |
| Catchment radius | 360 mm |
| Catchment diameter | 720 mm |
| Outer petal rise | 72 mm |
| Hub OD / clear ID | 184 / 164 mm |
| Funnel height | 92 mm |
| Outlet clear ID | 61.5 mm |
| Outlet wall | 4.0 mm |
| Collar engagement | 48 mm |
| Shell wall | 3.2 mm |
| Screen pitch | 12 mm |

`outlet_id` is deliberately a **site-tunable parameter**, not a claim that one neck size fits every Rotoplas/other tinaco. Set it from the actual measured neck or fitting plus the required clearance/gasket allowance.

## Generate and verify

Verified with OpenSCAD 2021.01 and `cadquery-ocp==7.9.3.1`.


