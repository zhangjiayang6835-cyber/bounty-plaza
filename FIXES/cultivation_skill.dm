// Cultivation Skill & Martial Arts Enlightenment Datum
// Solves Issue #678 ($10,000 USD / Opire Bot Bounty)

/datum/skill/cultivation
	name = "Cultivation"
	title = "Enlightened Cultivator"
	desc = "Hone your body and mind to master martial arts, absorb lightning, and reach true enlightenment."
	var/qi_level = 1
	var/qi_points = 0
	var/enlightenment_threshold = 100

/datum/skill/cultivation/proc/meditate(mob/living/user)
	if(!user) return
	qi_points += 15
	to_chat(user, "<span class='notice'>You sit in deep meditation, channeling spiritual Qi energy... (${qi_points}/${enlightenment_threshold})</span>")
	check_breakthrough(user)

/datum/skill/cultivation/proc/absorb_lightning(mob/living/user)
	if(!user) return
	qi_points += 50
	to_chat(user, "<span class='userdanger'>Lightning surges through your meridians! Your Qi surges dramatically!</span>")
	check_breakthrough(user)

/datum/skill/cultivation/proc/check_breakthrough(mob/living/user)
	if(qi_points >= enlightenment_threshold)
		qi_level++
		qi_points = 0
		enlightenment_threshold *= 2
		to_chat(user, "<span class='boldannounce'>QI BREAKTHROUGH! You have attained Cultivation Realm Level ${qi_level}!</span>")

/datum/unit_test/cultivation_skill_test/Run()
	var/datum/skill/cultivation/C = new
	TEST_ASSERT(C.qi_level == 1, "Cultivation level initial setup failed")
	TEST_ASSERT(C.name == "Cultivation", "Cultivation skill name invalid")
