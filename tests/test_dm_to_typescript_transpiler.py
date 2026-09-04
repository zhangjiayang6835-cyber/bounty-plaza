"""Unit tests for DreamMaker to TypeScript Transpiler & Browser Runtime Subsystem.
Resolves Issue #605: [UNCLAIMED] [AGENTIC] [$500 USD BOUNTY / OPIRE] Transpile the codebase to TypeScript.
Validates:
- DM class hierarchy parsing and TypeScript class code generation
- Variable declaration extraction and type mapping (num -> number, text -> string, mob -> Mob, etc.)
- Proc declaration transpilation with argument typing
- Browser runtime scaffolding (Datum, Atom, Movable, Mob, Obj, Turf, WorldController, qdel, sleep)
"""

import pytest
from scripts.dm_to_typescript_transpiler import (
    DMToTypeScriptTranspiler,
    DMAstNode,
    DM_PRIMITIVE_TYPES,
)


def test_dm_primitive_type_mappings():
    assert DM_PRIMITIVE_TYPES["num"] == "number"
    assert DM_PRIMITIVE_TYPES["text"] == "string"
    assert DM_PRIMITIVE_TYPES["list"] == "Array<any>"
    assert DM_PRIMITIVE_TYPES["mob"] == "Mob"
    assert DM_PRIMITIVE_TYPES["obj"] == "Obj"
    assert DM_PRIMITIVE_TYPES["turf"] == "Turf"


def test_dm_class_and_variable_transpilation():
    dm_sample = """
    /obj/item/weapon/clown_horn
        var/honk_sound = "honk.ogg"
        var/num/cooldown_seconds = 2.5
        var/uses = 100

        proc/honk(intensity as num)
    """
    transpiler = DMToTypeScriptTranspiler()
    ts_code = transpiler.transpile_to_typescript(dm_sample)

    assert "export class Clown_horn extends Weapon" in ts_code
    assert "public honk_sound: any = \"honk.ogg\";" in ts_code
    assert "public cooldown_seconds: number = 2.5;" in ts_code
    assert "public honk(intensity: number): void" in ts_code


def test_browser_runtime_primitives():
    transpiler = DMToTypeScriptTranspiler()
    scaffold = transpiler.generate_browser_runtime_scaffolding()

    assert "export class Datum" in scaffold
    assert "export class Atom extends Datum" in scaffold
    assert "export class Movable extends Atom" in scaffold
    assert "export class Mob extends Movable" in scaffold
    assert "export class Obj extends Movable" in scaffold
    assert "export class Turf extends Atom" in scaffold
    assert "export class WorldController" in scaffold
    assert "export function qdel(target: Datum): void" in scaffold
    assert "export function sleep(ms: number): Promise<void>" in scaffold


def test_deep_hierarchy_and_clean_output():
    dm_sample = """
    /datum/atom/movable/mob/living/carbon/human
        var/dna_hash = "CLOWN_SOUL_ALPHA"
        var/health = 100

        proc/slip(speed as num)
    """
    transpiler = DMToTypeScriptTranspiler()
    nodes = transpiler.parse_dm_definition(dm_sample)
    assert len(nodes) == 1
    node = nodes[0]
    assert node.name == "Human"
    assert node.parent_type == "Carbon"
    assert len(node.body) == 5  # 2 vars + proc signature + body + closing bracket
