/client/proc/process_key_input(key_code, is_down)
	if(!key_code)
		return

	// Non-blocking queue push prevents client network threads from locking SSinput
	var/datum/input_event/E = new(src, key_code, is_down)
	GLOB.input_queue += E

	// Trigger immediate tick wake if subsystem is dormant
	if(SSinput.can_fire && !SSinput.locked)
		SSinput.post_queue_check()
