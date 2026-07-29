/datum/controller/subsystem/input
	name = "Input"
	wait = 1
	priority = FIRE_PRIORITY_INPUT
	flags = SS_NO_INIT

	/// Active input queue array to process
	var/list/current_run = list()
	/// Lock flag to prevent recursive deadlocks during processing
	var/locked = FALSE

/datum/controller/subsystem/input/fire(resumed = FALSE)
	if(locked)
		return

	if(!resumed)
		if(!length(GLOB.keybindings))
			return
		// Clone queue atomically to avoid mid-iteration mutation locks
		current_run = GLOB.input_queue.Copy()
		GLOB.input_queue.Cut()

	locked = TRUE
	var/list/curr = current_run

	while(length(curr))
		var/datum/input_event/E = curr[length(curr)]
		curr.len--

		if(QDELETED(E) || !E.owner)
			continue

		// Execute event non-blockingly with panic protection
		try
			E.execute()
		catch(var/exception/e)
			log_game("SSinput exception during execution: [e.name] - [e.desc]")

		if(MC_TICK_CHECK)
			locked = FALSE
			return

	locked = FALSE
