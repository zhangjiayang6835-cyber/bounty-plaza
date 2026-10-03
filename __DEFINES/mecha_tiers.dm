```dm
// Mecha tier configurations
/list/mecha_tiers
/mecha_tiers += list(list(
    "name" = "Basic Mech",
    "tier" = MECHA_TIER_BASIC,
    "complexity" = MECHA_BASE_COMPLEXITY,
    "speed" = MECHA_BASIC_SPEED,
    "armor" = 10,
    "capacity" = 20,
    "slots" = 3
))

/mecha_tiers += list(list(
    "name" = "Advanced Mech",
    "tier" = MECHA_TIER_ADVANCED,
    "complexity" = MECHA_BASE_COMPLEXITY + MECHA_TIER_COMPLEXITY_BONUS,
    "speed" = MECHA_ADVANCED_SPEED,
    "armor" = 20,
    "capacity" = 30,
    "slots" = 4
))

/mecha_tiers += list(list(
    "name" = "Elite Mech",
    "tier" = MECHA_TIER_ELITE,
    "complexity" = MECHA_BASE_COMPLEXITY + (MECHA_TIER_COMPLEXITY_BONUS * 2),
    "speed" = MECHA_ELITE_SPEED,
    "armor" = 30,
    "capacity" = 40,
    "slots" = 5
))
```