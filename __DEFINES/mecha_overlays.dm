```dm
// Overlay definitions for mecha visual states
/proc/mecha_get_overlay(temp_state, damage_state)
    switch(temp_state)
        if(1 to MECHA_DEFAULT_TEMP_THRESHOLD - 10)
            return MECHA_OVERLAY_NORMAL
        if(MECHA_DEFAULT_TEMP_THRESHOLD to MECHA_EMERGENCY_TEMP_THRESHOLD - 10)
            return MECHA_OVERLAY_HEATED
        else
            return MECHA_OVERLAY_CRITICAL

/proc/mecha_get_light_color(temp_state, damage_state)
    if(temp_state >= MECHA_EMERGENCY_TEMP_THRESHOLD)
        return MECHA_LIGHT_RED
    else if(temp_state >= MECHA_DEFAULT_TEMP_THRESHOLD)
        return MECHA_LIGHT_YELLOW
    else
        return MECHA_LIGHT_GREEN
```