// Tung Tung Tung Sahur — Antagonist Module
// Bounty #3 — $67
// The legendary brainrot antagonist from the Italian brainrot wiki.
// Wields his bat and quotes the Paris Peace Accords of 1947.

/datum/antagonist/tung_tung_sahur
	name = "Tung Tung Tung Sahur"
	show_in_antagpanel = TRUE
	show_name_in_check_antagonists = TRUE
	antagpanel_category = "Antagonists"
	var/theme_music = 'sound/ambience/antag/sahur_theme.ogg'
	var/static/list/paris_peace_accords = list(
		"Article 1: The frontiers of Italy shall be those that existed on January 1, 1938.",
		"Article 2: The Free Territory of Trieste is hereby constituted.",
		"Article 3: Italy renounces all right and title to the Italian territorial possessions in Africa.",
		"Article 5: Italy recognizes and undertakes to respect the sovereignty and independence of Ethiopia.",
		"Article 6: Italy recognizes the sovereignty of Albania.",
		"Article 9: Italy shall take all measures necessary to secure to all persons under Italian jurisdiction the enjoyment of human rights.",
		"Article 10: Italy undertakes to dissolve all Fascist organizations.",
		"Article 15: Italy shall recognize the full force of the Treaties of Peace with Roumania, Bulgaria, and Hungary.",
		"Article 19: Italian armed forces shall be limited to a number sufficient for tasks of an internal character.",
		"Article 21: No prosecution shall be maintained against any person for having acted in favor of the Allied cause.",
		"Article 23: Italy surrenders all war material.",
		"Article 24: Italy undertakes not to manufacture any atomic weapon.",
		"Article 27: Italy recognizes the independence of the State of Israel.",
		"Article 29: The present Treaty shall be ratified and shall come into force upon deposit of ratifications.",
		"Article 31: All property, rights and interests in Germany of Italy and Italian nationals are transferred.",
		"Article 33: Italy waives all claims of any description against the Allied and Associated Powers.",
		"Annex VI: Provisions relating to the Italian Navy.",
		"Annex VII: Provisions relating to the Italian Air Force.",
		"Annex IX: Provisions relating to Italian possessions in the Dodecanese.",
		"Annex XI: Provisions relating to certain property in ceded territory.",
	)

/datum/antagonist/tung_tung_sahur/on_gain()
	. = ..()
	give_equipment()
	give_objective()
	play_theme()

/datum/antagonist/tung_tung_sahur/proc/play_theme()
	if(owner?.current)
		owner.current.playsound_local(get_turf(owner.current), theme_music, 100, FALSE)

/datum/antagonist/tung_tung_sahur/greet()
	. = ..()
	to_chat(owner, "<span class='boldannounce'>TUNG TUNG TUNG SAHUR! You are the Sahur antagonist. Recite the 1947 Paris Peace Accords and strike down any who defy the accords with your bat!</span>")

/datum/antagonist/tung_tung_sahur/proc/give_equipment()
	var/mob/living/carbon/human/H = owner.current
	if(istype(H))
		H.equip_to_slot_or_del(new /obj/item/melee/baseball_bat/sahur(H), ITEM_SLOT_HANDS)

/datum/antagonist/tung_tung_sahur/proc/give_objective()
	var/datum/objective/sahur_obj = new()
	sahur_obj.explanation_text = "Enforce the Paris Peace Accords of 1947 across the station by any means necessary!"
	sahur_obj.completed = TRUE
	sahur_obj.owner = owner
	objectives |= sahur_obj

/datum/antagonist/tung_tung_sahur/proc/speak_accords(mob/living/user)
	if(!user)
		return
	var/quote = pick(paris_peace_accords)
	user.say("TUNG TUNG TUNG! Pursuant to the 1947 Paris Peace Accords: [quote]")

/obj/item/melee/baseball_bat/sahur
	name = "Tung Tung Sahur Bat"
	desc = "A sacred wooden bat used by Tung Tung Tung Sahur to awaken the station and enforce the 1947 Paris Peace Accords."
	icon = 'icons/obj/items_and_weapons.dmi'
	icon_state = "baseball_bat"
	force = 20
	throwforce = 15

/obj/item/melee/baseball_bat/sahur/attack(mob/living/M, mob/living/user)
	. = ..()
	if(.)
		var/datum/antagonist/tung_tung_sahur/A = user.mind?.has_antag_datum(/datum/antagonist/tung_tung_sahur)
		if(A && prob(50))
			A.speak_accords(user)
		else if(prob(30))
			user.say("TUNG TUNG TUNG SAHUR!")
