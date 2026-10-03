```dm
// Utility modules
/obj/item/mecha_equipment/utility
    name = "utility module"
    icon_state = "utility_basic"
    complexity = MODULE_UTILITY_MODULE
    heat_generation = 0
    utility_flags = UTILITY_DEFAULT

/obj/item/mecha_equipment/utility/radiator
    name = "radiator"
    icon_state = "radiator"
    complexity = MODULE_RADIATOR
    heat_generation = 0
    heat_dissipation = MECHA_BASE_HEAT_DISSIPATION * MECHA_RADIATOR_MULTIPLIER
    utility_flags = UTILITY_RADIATOR

/obj/item/mecha_equipment/utility/fan
    name = "cooling fan"
    icon_state = "fan"
    complexity = MODULE_FAN
    heat_generation = 0
    heat_dissipation = MECHA_BASE_HEAT_DISSIPATION * MECHA_FAN_MULTIPLIER
    utility_flags = UTILITY_FAN

/obj/item/mecha_equipment/utility/camera_beacon
    name = "camera beacon"
    icon_state = "camera_beacon"
    complexity = MODULE_CAMERA_BEACON
    heat_generation = 0
    utility_flags = UTILITY_CAMERA
    ai_access = MECHA_AI_ACCESS_BEACON

/obj/item/mecha_equipment/utility/thermal_visor
    name = "thermal visor"
    icon_state = "thermal_visor"
    complexity = MODULE_THERMAL_VISOR
    heat_generation = 0
    utility_flags = UTILITY_VISION
    visibility_modifier = 1.0

/obj/item/mecha_equipment/utility/improvised_mirror
    name = "improvised mirror"
    icon_state = "improvised_mirror"
    complexity = MODULE_IMPROVISED_MIRROR
    heat_generation = 0
    utility_flags = UTILITY_VISION
    visibility_modifier = 0.8
```