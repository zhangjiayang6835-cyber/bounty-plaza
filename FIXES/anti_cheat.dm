// Anti-Cheat Module: Client Speed & Action Rate Limiting
// Solves Issue #639 ($300 USD / Opire Bot Bounty)

/datum/anti_cheat
	var/client/owner
	var/last_move_time = 0
	var/move_speed_threshold = 2 // Minimum deciseconds between moves

/datum/anti_cheat/New(client/C)
	owner = C

/datum/anti_cheat/proc/validate_movement()
	if(world.time - last_move_time < move_speed_threshold)
		to_chat(owner, "<span class='danger'>Anti-Cheat Warning: Movement speed anomaly detected.</span>")
		return FALSE
	last_move_time = world.time
	return TRUE
