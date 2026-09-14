// TempleOS Compatibility Module for SlopStation13
// "Bounty completed! That's another epic level cleared in this game called life! Level up!"
// Bounty #4 — $640 Bohemian Dollars
// Restores TempleOS player access with ancient Sumerian welcome

/**
 * TempleOS Compatibility System
 *
 * Restores compatability for our TempleOS players (48% of playerbase)
 * with proper ancient Sumerian greetings and title screen.
 */
/datum/templeos_compat
	var/name = "TempleOS Compatability Layer"
	var/version = "1.0.0"
	var/enabled = TRUE
	var/static/list/sumerian_greetings = list(
		"𒊕𒅍 𒄀𒈾 𒀭𒂗𒆤𒂵 — Silim he-me-en? (Greetings, are you well?)",
		"𒀭𒂗𒆤 𒄯𒊏𒀭𒂵 — Dingir Enlil hur-sag-ga (Lord Enlil of the mountain)",
		"𒂍𒃲 𒈗𒀀𒉌 — E-gal lugal-a-ni (The great house of his king)",
		"𒄑𒂞 𒄀𒈾𒉡𒌝 — Gish-gigir gi-na-nu-um (The chariot is prepared)",
		"𒀭𒈹 𒅆𒂍𒀀 — Dingir Inanna shi-e-a (Goddess Inanna, look upon me)",
		"𒇽 𒃻 𒄖𒌌 — Lu ninda gu-ul (The man eats bread greatly)",
		"𒀀 𒈾 𒈨 𒂗 — A na me-en? (What are you?)",
		"𒄑𒈣 𒈣𒇲 — Gish-ma magur-gal (The great ship)",
		"𒄀𒊑 𒋗 𒁕𒈠𒀠 — Gi-ri shu da-ma-al (The path is broad)",
		"𒂍𒀀𒉌 𒆍𒃲 — E-a-ni ka-gal (His house, the great gate)",
	)
	var/static/list/templeos_wisdom = list(
		"God says: love Me with all thy heart, mind, and soul.",
		"In the beginning, God created the heavens and the earth.",
		"Through HolyC, all things are possible.",
		"The temple is not made with hands — it is built in the spirit.",
		"Terry A. Davis saw the truth. We honor his vision.",
		"640x480 16 colors — the resolution of prophets.",
		"God's VGA mode is the one true display mode.",
		"Thou shalt not use ring 3 — stay in ring 0.",
		"Simon Peter saith: compile ye first the HolyC.",
	)
	var/list/templeos_players = list()
	var/templeos_player_count = 0

// Global instance
/var/global/datum/templeos_compat/templeos = new()

/**
 * Welcome back TempleOS users
 */
/proc/welcome_templeos_players(mob/player)
	if(!global.templeos?.enabled)
		return

	global.templeos.templeos_player_count++
	global.templeos.templeos_players += player

	// Ancient Sumerian greeting
	var/greeting = pick(global.templeos.sumerian_greetings)
	to_chat(player, span_big(span_greentext("𒋰𒁀𒀀𒋾 — TAB-BA-A-TI (Welcome back, companion!)")))
	to_chat(player, span_notice(greeting))
	to_chat(player, span_boldnotice("Welcome back, TempleOS warrior! 48% of our crew missed you!"))

	// Play welcome sound
	playsound(player, 'sound/misc/templeos_welcome.ogg', 50, TRUE)

	// Show TempleOS-optimized HUD
	player.client?.screen += new/atom/movable/screen/templeos_border()

	// Wisdom message
	spawn(50)
		to_chat(player, span_notice("TempleOS Wisdom: [pick(global.templeos.templeos_wisdom)]"))

// TempleOS title screen handler
/atom/movable/screen/templeos_title
	name = "TempleOS Welcome Screen"
	icon = 'icons/misc/templeos.dmi'
	icon_state = "templeos_title"
	screen_loc = "CENTER,CENTER"
	layer = SCREEN_LAYER + 1
	plane = FULLSCREEN_PLANE
	mouse_opacity = MOUSE_OPACITY_TRANSPARENT

/atom/movable/screen/templeos_title/Initialize()
	. = ..()
	// Ancient Sumerian title
	var/obj/effect/templeos_welcome_text/T = new()
	T.maptext = "<span style='font-size: 24pt; color: #FFD700; text-align: center; font-family: "Courier New"'>𒊕𒅍 𒄀𒈾<br>SLOPSTATION 13<br>TempleOS Edition<br><span style='font-size: 12pt'>Welcome back, ancient ones</span></span>"
	T.screen_loc = "CENTER,CENTER+2"
	add_overlay(T)

/atom/movable/screen/templeos_border
	name = "TempleOS Border"
	icon = 'icons/misc/templeos.dmi'
	icon_state = "templeos_border"
	screen_loc = "CENTER,CENTER"
	layer = SCREEN_LAYER
	plane = FULLSCREEN_PLANE
	mouse_opacity = MOUSE_OPACITY_TRANSPARENT

// TempleOS compatibility check
/proc/check_templeos_compat()
	if(!global.templeos?.enabled)
		return FALSE

	// Verify all TempleOS-critical files exist
	var/static/list/critical_files = list(
		"code/modules/templeos/templeos_compat.dm"
	)

	for(var/file in critical_files)
		if(!fexists(file))
			log_game("TEMPLEOS WARNING: Missing critical file: [file]")
			message_admins("TEMPLEOS COMPAT WARNING: Missing [file]")
			return FALSE

	return TRUE

// TempleOS admin panel
/client/proc/templeos_panel()
	set category = "Server"
	set name = "TempleOS Compatability Panel"

	if(!check_rights(R_SERVER))
		return

	var/dat = "<html><head><title>TempleOS Compatability</title></head><body>"
	dat += "<h2>🏛️ TempleOS Compatability Panel</h2>"
	dat += "<b>Status:</b> [global.templeos?.enabled ? "ENABLED" : "DISABLED"]<br>"
	dat += "<b>Active TempleOS Players:</b> [global.templeos?.templeos_player_count]<br>"
	dat += "<b>Version:</b> [global.templeos?.version]<br>"
	dat += "<hr>"
	dat += "<a href='?src=[REF(src)];templeos_toggle=1'>Toggle TempleOS Mode</a><br>"
	dat += "<a href='?src=[REF(src)];templeos_greet=1'>Broadcast Sumerian Greeting</a><br>"
	dat += "</body></html>"

	usr << browse(dat, "window=templeos;size=400x300")

// TempleOS compatibility item
/obj/item/templeos_bible
	name = "TempleOS Holy Bible"
	desc = "A Bible blessed by Terry A. Davis himself. Contains the true Word of God in HolyC."
	icon = 'icons/obj/storage.dmi'
	icon_state = "bible"
	item_state = "bible"
	w_class = WEIGHT_CLASS_SMALL

/obj/item/templeos_bible/attack_self(mob/user)
	to_chat(user, span_notice("You open the TempleOS Bible and read..."))
	to_chat(user, span_greentext("[pick(global.templeos.templeos_wisdom)]"))
	playsound(src, 'sound/effects/pray.ogg', 30, TRUE)

// TempleOS prayer emote
/datum/emote/living/templeos_pray
	key = "tpray"
	key_third_person = "tprays"
	message = "raises their hands to the heavens and prays in ancient Sumerian!"
	message_mime = "silently gestures ancient Sumerian prayers!"
	emote_type = EMOTE_VISIBLE

/datum/emote/living/templeos_pray/run_emote(mob/user, params)
	. = ..()
