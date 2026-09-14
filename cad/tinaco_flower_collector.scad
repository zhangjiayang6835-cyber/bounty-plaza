$fn = 72;
PETAL_COUNT = 8;
OUTER_RADIUS = 850.0;
INNER_RADIUS = 225.0;
SLOPE_DEG = 18.5;
WALL_THICKNESS = 4.0;
LIP_HEIGHT = 45.0;
THROAT_DIAMETER = 450.0;
DRAIN_NECK_DIAMETER = 110.0;
FUNNEL_DEPTH = 180.0;
ADAPTER_NOMINAL_DIA = 500.0;
ADAPTER_MIN_DIA = 400.0;
ADAPTER_MAX_DIA = 650.0;
ADAPTER_HEIGHT = 120.0;
ADAPTER_THICKNESS = 5.0;

module single_petal_sweep() {
    span_angle = (360.0 / PETAL_COUNT) + 6.0;
    rotate_extrude(angle = span_angle, convexity = 10)
    translate([INNER_RADIUS, 0, 0])
    polygon(points = [
        [0, 0],
        [OUTER_RADIUS - INNER_RADIUS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG)],
        [OUTER_RADIUS - INNER_RADIUS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) + LIP_HEIGHT],
        [OUTER_RADIUS - INNER_RADIUS - WALL_THICKNESS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) + LIP_HEIGHT],
        [OUTER_RADIUS - INNER_RADIUS - WALL_THICKNESS, (OUTER_RADIUS - INNER_RADIUS) * tan(SLOPE_DEG) - WALL_THICKNESS],
        [0, -WALL_THICKNESS]
    ]);
}

module flower_petals_array() {
    for (i = [0 : PETAL_COUNT - 1]) {
        rotate([0, 0, i * (360.0 / PETAL_COUNT)])
        single_petal_sweep();
    }
}

module central_drain_funnel() {
    difference() {
        cylinder(h = FUNNEL_DEPTH, r1 = DRAIN_NECK_DIAMETER / 2.0 + WALL_THICKNESS, r2 = THROAT_DIAMETER / 2.0 + WALL_THICKNESS, center = false);
        translate([0, 0, -1])
        cylinder(h = FUNNEL_DEPTH + 2, r1 = DRAIN_NECK_DIAMETER / 2.0, r2 = THROAT_DIAMETER / 2.0, center = false);
    }
}

module anti_vortex_vanes() {
    for (j = [0 : 3]) {
        rotate([0, 0, j * 90])
        translate([0, -WALL_THICKNESS / 2.0, 0])
        cube([THROAT_DIAMETER / 2.0 - 10.0, WALL_THICKNESS, FUNNEL_DEPTH * 0.75]);
    }
}

module adjustable_tinaco_adapter_collar() {
    r_in = ADAPTER_NOMINAL_DIA / 2.0;
    r_out = r_in + ADAPTER_THICKNESS;
    difference() {
        union() {
            cylinder(h = ADAPTER_HEIGHT, r = r_out, center = false);
            translate([0, 0, ADAPTER_HEIGHT - 20])
            cylinder(h = 20, r = r_out + 35, center = false);
        }
        translate([0, 0, -2])
        cylinder(h = ADAPTER_HEIGHT + 4, r = r_in, center = false);
        for (s = [0 : 3]) {
            rotate([0, 0, s * 90])
            translate([-10, -5, -1])
            cube([r_out + 50, 10, ADAPTER_HEIGHT + 2]);
        }
    }
}

module debris_filter_screen() {
    difference() {
        cylinder(h = 10, r = DRAIN_NECK_DIAMETER / 2.0 + 5, center = false);
        translate([0, 0, -1])
        cylinder(h = 12, r = DRAIN_NECK_DIAMETER / 2.0 - 8, center = false);
    }
}

module tinaco_rainwater_harvester_assembly() {
    color([0.2, 0.7, 0.9, 0.85])
    flower_petals_array();

    color([0.15, 0.5, 0.8, 1.0])
    translate([0, 0, -FUNNEL_DEPTH])
    union() {
        central_drain_funnel();
        anti_vortex_vanes();
    }

    color([0.3, 0.3, 0.35, 1.0])
    translate([0, 0, -FUNNEL_DEPTH - ADAPTER_HEIGHT])
    adjustable_tinaco_adapter_collar();

    color([0.8, 0.8, 0.85, 1.0])
    translate([0, 0, -FUNNEL_DEPTH + 15])
    debris_filter_screen();
}

tinaco_rainwater_harvester_assembly();
