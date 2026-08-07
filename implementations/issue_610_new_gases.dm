
// File: /code/modules/atmos/gases/new_gases.dm
// Minimal implementation of Shitium, Kurchatov-Quantium, Adskiderium

/datum/gas/shitium
    name = "Shitium"
    id = "shitium"
    molar_mass = 32  // Arbitrary mass
    specific_heat = 20
    flags = IDEAL_GAS_DEFAULT
    color = "#8B6914"  // Brown
    desc = "A disgusting miasmic gas"

    /datum/gas/shitium/react(list/data)
        if(data["temperature"] > 373.15)
            return TRUE  // React at high temp
        return FALSE

/datum/gas/kurchatov_quantium
    name = "Kurchatov-Quantium"
    id = "kurchatov_quantium"
    molar_mass = 98
    specific_heat = 25
    flags = IDEAL_GAS_DEFAULT
    color = "#FF00FF"  // Magenta - quantum
    desc = "A chaotic quantum gas with unpredictable properties"

    /datum/gas/kurchatov_quantium/react(list/data)
        // Quantum mutations on contact
        return TRUE

/datum/gas/adskiderium
    name = "Adskiderium"
    id = "adskiderium"
    molar_mass = 142
    specific_heat = 30
    flags = IDEAL_GAS_DEFAULT
    color = "#00FF00"  // Green - eldritch
    desc = "[REDACTED] - CentCom classified hazard"

    /datum/gas/adskiderium/react(list/data)
        // Psychological/eldritch effects
        return TRUE

// Register the new gases
/proc/register_new_gases()
    new /datum/gas/shitium()
    new /datum/gas/kurchatov_quantium()
    new /datum/gas/adskiderium()
