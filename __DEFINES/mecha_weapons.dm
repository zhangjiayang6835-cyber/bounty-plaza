```dm
// Weapon defines
#define WEAPON_TYPE_MELEE 1
#define WEAPON_TYPE_ENERGY 2
#define WEAPON_TYPE_PROJECTILE 3
#define WEAPON_TYPE_SPECIAL 4

// Weapon properties
#define WEAPON_AP_MODIFIER 1.0
#define WEARMOR_DEMO_MODIFIER 1.0
#define WEAPON_COOLDOWN_NORMAL 10
#define WEAPON_COOLDOWN_HEAVY 20

// Melee weapons
/obj/item/mecha_equipment/melee
    name = "melee weapon"
    icon_state = "melee_basic"
    equipment_delay = 15
    complexity = MODULE_SIMPLE_MELEE
    heat_generation = EQUIPMENT_HEAT_BASIC
    damage_force = 15
    damage_type = BRUTE
    attack_verb = list("smashed", "slashed", "cut")
    armor_penetration = 10
    demo_damage = 10

/obj/item/mecha_equipment/melee/advanced
    name = "advanced melee weapon"
    icon_state = "melee_advanced"
    complexity = MODULE_ADVANCED_MELEE
    heat_generation = EQUIPMENT_HEAT_BASIC * 1.5
    damage_force = 25
    armor_penetration = MODULE_MELEE_ARMOR_PIERCE
    demo_damage = MODULE_MELEE_DEMO_DAMAGE

// Energy weapons
/obj/item/mecha_equipment/weapon
    name = "energy weapon"
    icon_state = "energy_basic"
    equipment_delay = 20
    complexity = MODULE_BASIC_WEAPON
    heat_generation = EQUIPMENT_HEAT_ENERGY
    shot_cost = 10
    projectile_type = /obj/projectile/energy
    fire_sound = 'sound/weapons/laser.ogg'
    capacitor_delay = MECHA_BASE_CAPACITOR_DELAY

/obj/item/mecha_equipment/weapon/heavy
    name = "heavy energy weapon"
    icon_state = "energy_heavy"
    complexity = MODULE_HEAVY_WEAPON
    heat_generation = EQUIPMENT_HEAT_ENERGY * 1.5
    shot_cost = 20
    damage_force = 30
    fire_delay = 15
```