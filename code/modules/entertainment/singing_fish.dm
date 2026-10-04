/datum/singing_fish
	var/singing = FALSE
	var/song = "take me to the river"
	var/dancing = FALSE
	var/deempisi_was_here = FALSE

/datum/singing_fish/Initialize()
	. = ..()
	AddComponent(/datum/component/singing, song, TRUE)
	AddComponent(/datum/component/dancing)

/datum/singing_fish/proc/sing()
	singing = TRUE
	visible_message(span_notice("The fish begins to sing 'take me to the river'!"))
	playsound(loc, 'sound/voice/sopranos_oof_marone.ogg', 50, 1)

/datum/singing_fish/proc/dance()
	dancing = TRUE
	visible_message(span_notice("The fish starts dancing to the rhythm of the song!"))

/datum/singing_fish/proc/readd_deempisi()
	if(!deempisi_was_here)
		deempisi_was_here = TRUE
		var/mob/living/simple_animal/deempisi = new /mob/living/simple_animal/deempisi(loc)
		visible_message(span_notice("Mr. Deempisi has returned to the bar!"))

/obj/item/reagent_containers/food/snacks/fish/singing
	name = "singing fish"
	desc = "A fish that can sing and dance. OOF MARONE!"
	icon_state = "fish"
	le = FALSE
	bite_consumption = 5
	foodtypes = MEAT
	/// Reference to the singing fish datum
	var/datum/singing_fish/sing_datum

/obj/item/reagent_containers/food/snacks/fish/singing/Initialize()
	. = ..()
	sing_datum = new /datum/singing_fish()
	sing_datum.sing()
	sing_datum.dance()

/obj/item/reagent_containers/food/snacks/fish/singing/attack_self(mob/user)
	. = ..()
	if(!sing_datum)
		return
	sing_datum.sing()
	sing_datum.dance()
	user.visible_message(span_notice("[user] makes the fish sing and dance!"), span_notice("You make the fish sing and dance! OOF MARONE!"))

/obj/item/reagent_containers/food/snacks/fish/singing/Destroy()
	QDEL_NULL(sing_datum)
	return ..()

/mob/living/simple_animal/deempisi
	name = "Mr. Deempisi"
	desc = "The legendary bar fish. OOF MARONE!"
	icon = 'icons/mob/simple_animal.dmi'
	icon_state = "deempisi"
	speak_emote = list("sings")
	speak_chance = 1
	turns_per_move = 5
	response_help = "pokes"
	response_disarm = "shoves"
	response_harm = "hits"
	speed = 1
	stop_automated_movement = 0
	attack_sound = 'sound/weapons/tap.ogg'
	health = 50
	maxHealth = 50
	melee_damage_lower = 5
	melee_damage_upper = 5
	attacktext = "slaps"
	var/singing = FALSE

/mob/living/simple_animal/deempisi/Initialize()
	. = ..()
	AddComponent(/datum/component/singing, "take me to the river", TRUE)
	AddComponent(/datum/component/dancing)

/mob/living/simple_animal/deempisi/AttackingTarget()
	. = ..()
	if(. && isliving(target))
		var/mob/living/L = target
		if(prob(30))
			visible_message(span_warning("[src] slaps [L]! OOF MARONE!"))
			L.adjustBruteLoss(5)

/mob/living/simple_animal/deempisi/sing()
	singing = TRUE
	visible_message(span_notice("[src] begins to sing 'take me to the river'!"))
	playsound(loc, 'sound/voice/sopranos_oof_marone.ogg', 50, 1)

/mob/living/simple_animal/deempisi/dance()
	visible_message(span_notice("[src] starts dancing to the rhythm of the song!"))
/mob/living/simple_animal/deempisi/proc/readd()
	if(!singing)
		sing()
		dance()

// Add singing fish to bar
/obj/structure/fish_tank/bar_fish
	name = "bar fish tank"
	desc = "A fish tank containing a singing fish. OOF MARONE!"
	icon = 'icons/obj/flora.dmi'
	icon_state = "fish_tank"
	anchored = TRUE
	density = TRUE

/obj/structure/fish_tank/bar_fish/Initialize()
	. = ..()
	new /obj/item/reagent_containers/food/snacks/fish/singing(loc)
	new /mob/living/simple_animal/deempisi(loc)

// Add component for singing
/datum/component/singing
	var/song_name
	var/loop_singing

/datum/component/singing/Initialize(song, loop)
	if(!isitem(parent) && !ismob(parent))
		return COMPONENT_INCOMPATIBLE
	song_name = song
	loop_singing = loop

/datum/component/singing/sing()
	var/sound_to_play
	if(song_name == "take me to the river")
		sound_to_play = 'sound/voice/sopranos_oof_marone.ogg'
	else
		sound_to_play = 'sound/voice/singing.ogg'

	var/atom/singing_parent = parent
	singing_parent.visible_message(span_notice("[singing_parent] begins to sing '[song_name]'!"))
	playsound(singing_parent.loc, sound_to_play, 50, 1)
	if(loop_singing)
		addtimer(CALLBACK(src, PROC_REF(sing)), 30 SECONDS, TIMER_UNIQUE | TIMER_LOOP)

// Add component for dancing
/datum/component/dancing
	var/dance_moves = list("spin", "wiggle", "flop")

/datum/component/dancing/dance()
	var/atom/dancing_parent = parent
	var/dance_move = pick(dance_moves)
	dancing_parent.visible_message(span_notice("[dancing_parent] starts [dance_move]ing to the rhythm of the song!"))
	playsound(dancing_parent.loc, 'sound/effects/dancing.ogg', 30, 1)

// Add the bar fish tank to the bar area
/area/station/bar
	placeable = FALSE
	/obj/structure/fish_tank/bar_fish
		placeable = TRUE
		placeable_blacklist = list()

// Add the singing fish to the kitchen for good measure
/area/station/kitchen
	/obj/structure/fish_tank/bar_fish
		placeable = TRUE
		placeable_blacklist = list()