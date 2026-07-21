/**
 * Modifications to human mob code to support teeth organs.
 *
 * This file contains the modifications to the human mob code to support
 * teeth organs functionality. The teeth organs are implemented as a list
 * of organ objects, with each organ representing a tooth.
 *
 * The teeth organs functionality is used by the Dentist job to perform
 * dental procedures and maintain the health of the crew's teeth.
 */

#include "carbon.dm"

obj/mob/living/carbon/human = obj/mob/living/carbon
    // Teeth organs functionality
    var/teeth_organs = list()

    // Initialize teeth organs
    proc/init_teeth_organs()
        teeth_organs = list()
        for (var/organ in /datum/organ/teeth)
            teeth_organs[organ] = new /datum/organ/teeth(organ)

    // Update teeth organs
    proc/update_teeth_organs()
        for (var/organ in teeth_organs)
            organ.update()

    // Handle teeth organs damage
    proc/handle_teeth_damage(damage)
        for (var/organ in teeth_organs)
            organ.handle_damage(damage)

    // Heal teeth organs
    proc/heal_teeth_organs(amount)
        for (var/organ in teeth_organs)
            organ.heal(amount)

    // Check teeth organs health
    proc/check_teeth_health()
        var/total_health = 0
        for (var/organ in teeth_organs)
            total_health += organ.health

        return total_health / teeth_organs.length

    // Initialize the human mob
    proc/init()
        ..()
        init_teeth_organs()