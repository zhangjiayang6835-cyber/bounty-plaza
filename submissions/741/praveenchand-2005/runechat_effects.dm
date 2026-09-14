// Runescape-inspired chat effects for runechat maptext.
// Bounty #371 - 500 USD
// Colour and motion effects applied to runechat maptext rendering.

#define RUNECHAT_EFFECT_YELLOW "#ffff00"
#define RUNECHAT_EFFECT_RED "#ff0000"
#define RUNECHAT_EFFECT_GREEN "#00ff00"
#define RUNECHAT_EFFECT_CYAN "#00ffff"
#define RUNECHAT_EFFECT_PURPLE "#800080"
#define RUNECHAT_EFFECT_WHITE "#ffffff"

/datum/runechat_effect
	var/name = ""
	var/effect_type = "colour" // colour, flash, glow, motion
	var/css_class = ""

/datum/runechat_effect/New(name, effect_type, css_class)
	src.name = name
	src.effect_type = effect_type
	src.css_class = css_class

/datum/runechat_effects
	var/static/list/registry = list()

/datum/runechat_effects/New()
	. = ..()
	// Solid colour effects (yellow is the default)
	register("yellow", "colour", "runechat-colour-yellow")
	register("red", "colour", "runechat-colour-red")
	register("green", "colour", "runechat-colour-green")
	register("cyan", "colour", "runechat-colour-cyan")
	register("purple", "colour", "runechat-colour-purple")
	register("white", "colour", "runechat-colour-white")

	// Flash effects (two-tone flashing)
	register("flash1", "flash", "runechat-flash-flash1")
	register("flash2", "flash", "runechat-flash-flash2")
	register("flash3", "flash", "runechat-flash-flash3")

	// Glow effects (multi-colour fades) + rainbow
	register("glow1", "glow", "runechat-glow-glow1")
	register("glow2", "glow", "runechat-glow-glow2")
	register("glow3", "glow", "runechat-glow-glow3")
	register("rainbow", "glow", "runechat-glow-rainbow")

	// Motion effects
	register("wave", "motion", "runechat-wave")
	register("wave2", "motion", "runechat-wave2")
	register("shake", "motion", "runechat-shake")
	register("slide", "motion", "runechat-slide")
	register("scroll", "motion", "runechat-scroll")

/datum/runechat_effects/proc/register(name, effect_type, css_class)
	if(name in registry)
		return
	registry[name] = new/datum/runechat_effect(name, effect_type, css_class)

/datum/runechat_effects/proc/resolve(name)
	return registry[name]

/datum/runechat_effects/proc/all_names()
	return registry
