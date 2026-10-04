/**
 * PuzzleScript - A minimalist puzzle game engine for SS13
 * 
 * This module implements PuzzleScript games in SS13 via WebView
 * Reference: https://www.puzzlescript.net/
 *          https://github.com/increpare/PuzzleScript
 */

/obj/item/puzzlescript_game
	name = "PuzzleScript Game"
	desc = "A portable puzzle game engine. Right-click to play!"
	icon = 'icons/obj/devices.dmi'
	icon_state = "gameboy"
	var/game_data = null
	var/current_level = 1

/obj/item/puzzlescript_game/Initialize(mapload)
	. = ..()
	// Default to a simple Sokoban-like game
	game_data = get_default_puzzlescript()

/obj/item/puzzlescript_game/attack_self(mob/user)
	show_puzzlescript_view(user)

/obj/item/puzzlescript_game/proc/show_puzzlescript_view(mob/user)
	var/datum/browser/puzzle_browser = new(user, "puzzlescript", "PuzzleScript Game", 800, 600)
	puzzle_browser.set_content(generate_puzzlescript_html())
	puzzle_browser.open()

/obj/item/puzzlescript_game/proc/generate_puzzlescript_html()
	// This is a minimal implementation that loads the PuzzleScript engine
	// and runs a simple Sokoban-like game
	return {"
		<!DOCTYPE html>
		<html>
		<head>
			<title>PuzzleScript Game</title>
			<style>
				body { margin: 0; background: #1a1a1a; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: monospace; }
				#gameCanvas { border: 2px solid #444; image-rendering: pixelated; }
				#controls { position: absolute; bottom: 20px; color: white; text-align: center; }
			</style>
		</head>
		<body>
			<canvas id="gameCanvas"></canvas>
			<div id="controls">
				<p>Arrow Keys or WASD to move | R to restart</p>
				<p>Level: [current_level]</p>
			</div>
			<script src='https://cdn.jsdelivr.net/gh/increpare/PuzzleScript@master/build/puzzlescript.js'></script>
			<script>
				// Simple Sokoban-like PuzzleScript game
				var gameJSON = [game_data];
				
				var game = new PuzzleScriptEngine({
					canvas: document.getElementById("gameCanvas"),
					gameData: gameJSON
				});
				
				game.run();
				
				// Keyboard controls
				document.addEventListener('keydown', function(e) {
					if (e.key === 'r' || e.key === 'R') {
					 game.restart();
					}
				});
			</script>
		</body>
		</html>
	"}

/obj/item/puzzlescript_game/proc/get_default_puzzlescript()
	// Default simple Sokoban-like game in PuzzleScript format
	return {"
		{
		  "TITLE": "Sokoban SS13",
		  "DESCRIPTION": "Push all the crates to the targets!",
		  "AUTHOR": "SS13 Bounty",
		  "VIEWPORT": {
		 "WIDTH": 10,
		 "HEIGHT": 10
		  },
		  "LEGEND": {
		 "0": "EMPTY",
		 "1": "WALL",
		 "2": "PLAYER",
		 "3": "CRATE",
		 "4": "TARGET",
		 "5": "CRATE_ON_TARGET"
		  },
		  "SOLVED": "LEVEL_COMPLETE",
		  "LEVELS": [
		 [
		 "1111111111",
		 "1000000001",
		 "1003200001",
		 "1000400001",
		 "1000000001",
		 "1000000001",
		 "1000000001",
		 "1000000001",
		 "1000000001",
		 "1111111111"
		 ]
		  ]
		}
	"}

/obj/machinery/computer/puzzlescript_terminal
	name = "PuzzleScript Terminal"
	desc = "A computer terminal for playing PuzzleScript games."
	icon = 'icons/obj/computer.dmi'
	icon_state = "computer"
	var/obj/item/puzzlescript_game/game_cartridge = null

/obj/machinery/computer/puzzlescript_terminal/Initialize(mapload)
	. = ..()
	game_cartridge = new /obj/item/puzzlescript_game(src)

/obj/machinery/computer/puzzlescript_terminal/attack_hand(mob/user)
	if(game_cartridge)
		game_cartridge.show_puzzlescript_view(user)
	else
		to_chat(user, span_warning("No game cartridge inserted!"))

/obj/item/puzzlescript_cartridge
	name = "PuzzleScript Cartridge"
	desc = "A game cartridge for PuzzleScript terminals."
	icon = 'icons/obj/devices.dmi'
	icon_state = "card"
	var/game_data = null

/obj/item/puzzlescript_cartridge/attack_self(mob/user)
	if(game_data)
		var/obj/item/puzzlescript_game/temp_game = new /obj/item/puzzlescript_game()
		temp_game.game_data = game_data
		temp_game.show_puzzlescript_view(user)
		qdel(temp_game)
	else
		to_chat(user, span_warning("No game data on this cartridge!"))

// Add a simple puzzle game to the vending machine
/obj/machinery/vending/game_vendor
	name = "Game Vendor"
	desc = "Vends puzzle games and cartridges."
	icon_state = "syndi"
	icon_deny = "syndi-deny"
	product_slogans = list("Get your puzzle fix!", "Push crates, not buttons!")

/obj/machinery/vending/game_vendor/Initialize(mapload)
	. = ..()
	product_list[/obj/item/puzzlescript_game] = 5
	product_list[/obj/item/puzzlescript_cartridge] = 10

// Add a simple puzzle to the library
/obj/item/book/puzzlescript_manual
	name = "PuzzleScript Manual"
	desc = "A manual on how to create PuzzleScript games."
	icon = 'icons/obj/books.dmi'
	icon_state = "book"
	item_state = "book"
	author = "SS13 Development Team"

/obj/item/book/puzzlescript_manual/attack_self(mob/user)
	to_chat(user, span_notice("The manual explains how to create simple puzzle games using the PuzzleScript language. You can find more information at puzzlescript.net."))
	// In a full implementation, this could open a guide or tutorial