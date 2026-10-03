<content>
// Flower-shaped rainwater collector for a tinaco
// Parametric design for easy customization
// Designed for Mexico City climate and standard tinaco sizes

// Parameters - customize these values
tinaco_diameter = 1200; // mm, typical tinaco diameter
tinaco_height = 1500; // mm, typical tinaco height
petal_count = 8; // number of petals in the flower
petal_width = 300; // mm, width of each petal
petal_length = 600; // mm, length of each petal
funnel_height = 200; // mm, height of the funnel collector
funnel_width = 400; // mm, width at the top of the funnel
drain_pipe_diameter = 50; // mm, standard drain pipe size
wall_thickness = 3; // mm, material thickness for 3D printing
support_angle = 15; // degrees, angle of support struts

// Main module
module flower_collector() {
    difference() {
        // Create the main flower shape
        union() {
            // Central funnel
            translate([0, 0, 0])
            cylinder(h = funnel_height, d1 = funnel_width * 0.6, d2 = funnel_width, $fn = 64);
            
            // Flower petals
            for (i = [0:petal_count-1]) {
                rotate([0, 0, i * 360/petal_count])
                petal_shape();
            }
            
            // Support structure
            supports();
        }
        
        // Remove inner space for water flow
        translate([0, 0, wall_thickness])
        cylinder(h = funnel_height - wall_thickness, d1 = funnel_width * 0.6 - wall_thickness*2, d2 = funnel_width - wall_thickness*2, $fn = 64);
        
        // Drain pipe hole
        translate([0, 0, -funnel_height/2])
        cylinder(h = funnel_height, d = drain_pipe_diameter, $fn = 32);
    }
}

// Petal shape module
module petal_shape() {
    hull() {
        // Inner connection point
        translate([petal_width/2, 0, 0])
        cylinder(h = wall_thickness, d = wall_thickness * 3, $fn = 16);
        
        // Outer petal tip
        translate([petal_width + petal_length, 0, 0])
        cylinder(h = wall_thickness, d = petal_width, $fn = 32);
        
        // Middle points for smooth curve
        translate([petal_width + petal_length/3, -petal_width/3, 0])
        cylinder(h = wall_thickness, d = petal_width * 0.8, $fn = 24);
        
        translate([petal_width + petal_length/3, petal_width/3, 0])
        cylinder(h = wall_thickness, d = petal_width * 0.8, $fn = 24);
    }
}

// Support structure module
module supports() {
    // Radial supports
    for (i = [0:petal_count-1]) {
        rotate([0, 0, i * 360/petal_count + 360/petal_count/2])
        translate([funnel_width/2, 0, 0])
        rotate([support_angle, 0, 0])
        cube([petal_length/2, wall_thickness*2, wall_thickness], center = true);
    }
    
    // Top ring
    translate([0, 0, funnel_height])
    cylinder(h = wall_thickness, d = funnel_width + petal_width, $fn = 64);
    
    // Bottom ring
    translate([0, 0, 0])
    cylinder(h = wall_thickness, d = funnel_width, $fn = 64);
}

// Generate the model
flower_collector();

// Optional: Add mounting holes
module mounting_holes() {
    hole_count = 4;
    for (i = [0:hole_count-1]) {
        rotate([0, 0, i * 360/hole_count])
        translate([funnel_width/2 + 50, 0, wall_thickness])
        cylinder(h = funnel_height - wall_thickness*2, d = 10, $fn = 16);
    }
}

// Uncomment to add mounting holes
// mounting_holes();
</content>