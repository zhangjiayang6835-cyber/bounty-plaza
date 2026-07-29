// Environmental Event: Eternal Despair
// Solves Issue #676 ($200 USD / Opire Bot Bounty)

/datum/round_event/eternal_despair
	name = "Eternal Despair"
	announceWhen = 5

/datum/round_event/eternal_despair/announce()
	priority_announce("An ominous shadow engulfs the station... Eternal Despair has arrived!", "Station Alert", 'sound/effects/despair_horn.ogg')

/datum/round_event/eternal_despair/start()
	for(var/mob/living/carbon/human/H in GLOB.human_list)
		H.hallucination += 50
		to_chat(H, "<span class='userdanger'>You feel a chilling sense of absolute despair creeping in...</span>")
