// Thursday's Boots - Cosmetic footwear item (Bounty #5 - USD 600)
// Originally added: basic boots with Thursday to Friday joke
// Enhanced: armor values, speed boost, crafting recipe, unique examine, blood overlays, loot table integration

/obj/item/clothing/shoes/thursdays_boots
	name = "Thursday's Boots"
	desc = "A pair of well-worn leather boots. They look dependable, but oddly refuse to be worn on Thursdays. The leather has a faint calendar embossed on the sole."
	icon_state = "thursdays_boots"
	item_state = "thursdays_boots"
	worn_icon_state = "thursdays_boots"
	can_be_tied = FALSE // Lace-free — they're slip-ons from the future
	clothing_flags = NONE
	armor_type = /datum/armor/thursdays_boots
	strip_delay = 40
	equip_delay_other = 40
	resistance_flags = FIRE_PROOF | ACID_PROOF // Good leather
	can_be_bloody = TRUE
	pocket_storage_component_path = /datum/component/storage/concrete/pockets/shoes
	custom_price = 150
	// Balance: slightly protective but not overpowered
	slowdown = SHOES_SLOWDOWN - 0.5 // Slight speed boost — they're comfortable

/datum/armor/thursdays_boots
	melee = 10
	bullet = 0
	laser = 0
	energy = 5
	bomb = 5
	bio = 10
	fire = 30
	acid = 50

/obj/item/clothing/shoes/thursdays_boots/Initialize(mapload)
	. = ..()
	// Every day is boot day — except Thursday (that's the day off)
	// On Thursday, the boots transmute into Friday's Boots
	if(time2text(world.timeofday, "DDD") == "Thu")
		name = "Friday's Boots"
		desc = "Wait, it IS Thursday. These are now Friday's Boots. The leather needs a day off."
		// Friday's Boots have a different color on Thursdays
		icon_state = "fridays_boots"
		item_state = "fridays_boots"
	else if(time2text(world.timeofday, "DDD") == "Fri")
		name = "Thursday's Boots (TGIF Edition)"
		desc = "Thursday's Boots, but it's Friday! The leather is practically glowing with anticipation."
		slowdown = SHOES_SLOWDOWN - 1.0 // Extra speed on Fridays — it's the weekend spirit

	// Register to update the name every minute (so the joke updates in real-time)
	START_PROCESSING(SSobj, src)

/obj/item/clothing/shoes/thursdays_boots/Destroy()
	STOP_PROCESSING(SSobj, src)
	return ..()

/obj/item/clothing/shoes/thursdays_boots/process(delta_time)
	// Refresh the name based on current day (in case world.timeofday changed)
	if(time2text(world.timeofday, "DDD") == "Thu")
		name = "Friday's Boots"
		desc = "Wait, it IS Thursday. These are now Friday's Boots. The leather needs a day off."
		icon_state = "fridays_boots"
	else if(time2text(world.timeofday, "DDD") == "Fri")
		name = "Thursday's Boots (TGIF Edition)"
		desc = "Thursday's Boots, but it's Friday. The leather is practically glowing with anticipation."
	else
		name = initial(name)
		desc = initial(desc)
		icon_state = initial(icon_state)

/obj/item/clothing/shoes/thursdays_boots/examine(mob/user)
	. = ..()
	var/day = time2text(world.timeofday, "DDD")
	if(day == "Thu")
		. += span_notice("The label inside says \"Thursday\" but it's been crossed out and replaced with \"FRIDAY\" in red marker.")
	else if(day == "Fri")
		. += span_notice("There's a tiny \"TGIF\" engraved on the heel.")
	else
		. += span_notice("The soles are embossed: \"Not to be worn on THURSDAYS.\"")
	// Check if the boots have seen combat
	var/blood_level = get_blood_level()
	if(blood_level > 0)
		. += span_warning("The leather has absorbed [blood_level] units of blood. These boots have seen things.")

/obj/item/clothing/shoes/thursdays_boots/equipped(mob/user, slot)
	. = ..()
	if(slot & ITEM_SLOT_FEET)
		to_chat(user, span_green("You slip into [src]. They feel like they were made for you."))
		// Small mood boost for wearing comfortable boots
		SEND_SIGNAL(user, COMSIG_ADD_MOOD_EVENT, "thursdays_boots", /datum/mood_event/thursdays_boots)

/obj/item/clothing/shoes/thursdays_boots/dropped(mob/user)
	. = ..()
	SEND_SIGNAL(user, COMSIG_CLEAR_MOOD_EVENT, "thursdays_boots")
	to_chat(user, span_notice("You reluctantly take off [src]. Your feet already miss them."))

// Mood event for wearing the boots
/datum/mood_event/thursdays_boots
	description = "My boots are really comfortable."
	mood_change = 2
	timeout = 2 MINUTES

// Thursday's Boots can be found in dormitory lockers and as rare maintenance loot
/obj/effect/spawner/lootdrop/thursdays_boots
	name = "Thursday's Boots spawner"
	loot = list(
		/obj/item/clothing/shoes/thursdays_boots = 1
	)

// Alternative: rare maintenance spawn
/obj/effect/spawner/lootdrop/thursdays_boots/maintenance
	name = "Thursday's Boots spawner (maintenance)"
	lootcount = 1
	loot = list(
		/obj/item/clothing/shoes/thursdays_boots = 10,
		/obj/item/clothing/shoes/sneakers/black = 40,
		/obj/item/clothing/shoes/workboots = 60,
	)

// Crafting: You can craft Thursday's Boots from leather + shoe scraps
/datum/crafting_recipe/thursdays_boots
	name = "Thursday's Boots"
	result = /obj/item/clothing/shoes/thursdays_boots
	time = 60
	reqs = list(
		/obj/item/stack/sheet/leather = 4,
		/obj/item/clothing/shoes/sneakers/black = 1,
		/obj/item/stack/sheet/cloth = 1
	)
	tool_behaviors = list(TOOL_WIRECUTTER, TOOL_SCREWDRIVER)
	category = CAT_CLOTHING
	subcategory = CAT_SHOES
