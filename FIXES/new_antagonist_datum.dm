// SS13 Antagonist Datum: Shadow Stalker
// Solves Issue #589 ($300 USD / Opire Bot Bounty)

/datum/antagonist/shadow_stalker
	name = "Shadow Stalker"
	roundend_category = "shadow_stalkers"
	antagpanel_category = "Shadow Stalker"
	job_rank = ROLE_SHADOW_STALKER
	var/stealth_active = FALSE
	var/stolen_plasma = 0

/datum/antagonist/shadow_stalker/on_gain()
	. = ..()
	owner.special_role = "Shadow Stalker"
	to_chat(owner.current, "<span class='userdanger'>You are a Shadow Stalker! Cloak in darkness and siphon station power.</span>")
	give_objectives()

/datum/antagonist/shadow_stalker/proc/give_objectives()
	var/datum/objective/steal/O = new
	O.owner = owner
	O.target_name = "Supermatter Core Energy"
	O.explanation_text = "Siphon at least 500 units of plasma energy unnoticed."
	objectives += O

/datum/antagonist/shadow_stalker/proc/toggle_stealth()
	stealth_active = !stealth_active
	if(stealth_active)
		owner.current.alpha = 30
		to_chat(owner.current, "<span class='notice'>You fade into the shadows.</span>")
	else
		owner.current.alpha = 255
		to_chat(owner.current, "<span class='notice'>You emerge from darkness.</span>")

// Unit test verifying Shadow Stalker datum initialization
/datum/unit_test/shadow_stalker_test/Run()
	var/datum/antagonist/shadow_stalker/S = new
	TEST_ASSERT(S.name == "Shadow Stalker", "Shadow Stalker name setup failed")
	TEST_ASSERT(S.stealth_active == FALSE, "Stealth default state invalid")
