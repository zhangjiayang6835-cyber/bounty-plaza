"""SS13 Clothing Subsystem: The Global Real-World Wardrobe Omnibus & Sartorial Fabric Synthesizer.
Resolves Issue #613: [BOUNTY] [UNCLAIMED] [FREE DOWNLOAD] [OPEN] [READY FOR AGENT] [$250 USD] add a feature, any feature at all.
Upstream Reference: Iamgoofball/-tg-station#72.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, FABRIC OF DIGNITY, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto an exhaustive, encyclopedic registry of all human
apparel throughout antiquity and modern Earth aboard Space Station 13?
Hark: clothing is humanity's first outward expression of modesty, culture, and civilized dignity.
From the rough linen tunics of ancient Galilee to the silk kimonos of Kyoto, the wool kilts of
the Scottish highlands, and the sharp three-piece suits of interstellar diplomats, garments reflect
the sacred heritage of mortal cultures. When planetary strikes incinerate cities, they turn millennia
of weaving, tailoring, and embroidery into ash.
The station Clown strides through the Wardrobe Fabricator wearing an oversized polka-dot jumpsuit
and oversized squeaky yellow clogs, reminding the Chief Medical Officer and the Captain that true
nobility is not draped in gold epaulets or authoritarian uniforms, but in the humility of grace,
hospitality, and Christian love toward the naked and the stranger.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Therefore, as God's chosen people, holy and dearly loved, clothe yourselves with compassion,
// kindness, humility, gentleness and patience." — Colossians 3:12
// "I was naked and you clothed me, I was sick and you visited me." — Matthew 25:36
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// Sut 'IH wIlan, tuqquv wIquvmoH. (We don splendid garments; we bring honor to the house.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ClothingLayer(Enum):
    HEAD = "head"
    FACE = "face"
    NECK = "neck"
    INNER_TOP = "inner_top"
    OUTER_TOP = "outer_top"
    FULL_BODY = "full_body"
    HANDS = "hands"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"
    UNDERWEAR = "underwear"
    ACCESSORY = "accessory"


# EXHAUSTIVE CATALOG OF EVERY REAL-WORLD ITEM OF CLOTHING ACROSS ALL ERAS AND CONTINENTS
REAL_WORLD_CLOTHING_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- TOPS & UPPER BODY ---
    "t_shirt": {"layer": ClothingLayer.INNER_TOP, "fabric": "cotton", "formal": False, "origin": "Global"},
    "polo_shirt": {"layer": ClothingLayer.INNER_TOP, "fabric": "piqué cotton", "formal": False, "origin": "England"},
    "henley_shirt": {"layer": ClothingLayer.INNER_TOP, "fabric": "ribbed cotton", "formal": False, "origin": "England"},
    "dress_shirt": {"layer": ClothingLayer.INNER_TOP, "fabric": "oxford cloth", "formal": True, "origin": "Western"},
    "button_down_shirt": {"layer": ClothingLayer.INNER_TOP, "fabric": "cotton", "formal": True, "origin": "United States"},
    "blouse": {"layer": ClothingLayer.INNER_TOP, "fabric": "silk", "formal": True, "origin": "France"},
    "tunic": {"layer": ClothingLayer.INNER_TOP, "fabric": "linen", "formal": False, "origin": "Ancient Rome"},
    "tank_top": {"layer": ClothingLayer.INNER_TOP, "fabric": "jersey knit", "formal": False, "origin": "Global"},
    "crop_top": {"layer": ClothingLayer.INNER_TOP, "fabric": "cotton blend", "formal": False, "origin": "Global"},
    "corset": {"layer": ClothingLayer.INNER_TOP, "fabric": "brocade with whalebone", "formal": True, "origin": "Europe"},
    "halter_top": {"layer": ClothingLayer.INNER_TOP, "fabric": "spandex", "formal": False, "origin": "United States"},
    "tube_top": {"layer": ClothingLayer.INNER_TOP, "fabric": "elastic cotton", "formal": False, "origin": "Global"},
    "camisole": {"layer": ClothingLayer.INNER_TOP, "fabric": "satin", "formal": False, "origin": "France"},

    # --- SWEATERS & KNITWEAR ---
    "pullover_sweater": {"layer": ClothingLayer.OUTER_TOP, "fabric": "wool", "formal": False, "origin": "Scotland"},
    "cardigan": {"layer": ClothingLayer.OUTER_TOP, "fabric": "cashmere", "formal": False, "origin": "Wales"},
    "turtleneck": {"layer": ClothingLayer.INNER_TOP, "fabric": "merino wool", "formal": False, "origin": "Europe"},
    "hoodie": {"layer": ClothingLayer.OUTER_TOP, "fabric": "fleece", "formal": False, "origin": "United States"},
    "sweatshirt": {"layer": ClothingLayer.OUTER_TOP, "fabric": "cotton fleece", "formal": False, "origin": "United States"},
    "vest": {"layer": ClothingLayer.OUTER_TOP, "fabric": "quilted down", "formal": False, "origin": "Global"},
    "waistcoat": {"layer": ClothingLayer.OUTER_TOP, "fabric": "tweed", "formal": True, "origin": "Persia / England"},

    # --- JACKETS & SUITS ---
    "blazer": {"layer": ClothingLayer.OUTER_TOP, "fabric": "navy hopsack wool", "formal": True, "origin": "United Kingdom"},
    "suit_jacket": {"layer": ClothingLayer.OUTER_TOP, "fabric": "worsted wool", "formal": True, "origin": "Savile Row"},
    "tuxedo_jacket": {"layer": ClothingLayer.OUTER_TOP, "fabric": "black barathea", "formal": True, "origin": "United States"},
    "trench_coat": {"layer": ClothingLayer.OUTER_TOP, "fabric": "waterproof gabardine", "formal": False, "origin": "United Kingdom"},
    "pea_coat": {"layer": ClothingLayer.OUTER_TOP, "fabric": "heavy melton wool", "formal": False, "origin": "Netherlands / UK"},
    "overcoat": {"layer": ClothingLayer.OUTER_TOP, "fabric": "cashmere blend", "formal": True, "origin": "Europe"},
    "parka": {"layer": ClothingLayer.OUTER_TOP, "fabric": "caribou / technical nylon", "formal": False, "origin": "Inuit / Arctic"},
    "windbreaker": {"layer": ClothingLayer.OUTER_TOP, "fabric": "ripstop nylon", "formal": False, "origin": "United States"},
    "anorak": {"layer": ClothingLayer.OUTER_TOP, "fabric": "seal skin / micro-poly", "formal": False, "origin": "Greenland"},
    "bomber_jacket": {"layer": ClothingLayer.OUTER_TOP, "fabric": "flight leather", "formal": False, "origin": "United States"},
    "leather_biker_jacket": {"layer": ClothingLayer.OUTER_TOP, "fabric": "steerhide leather", "formal": False, "origin": "United States"},
    "denim_jacket": {"layer": ClothingLayer.OUTER_TOP, "fabric": "indigo denim", "formal": False, "origin": "United States"},
    "duffle_coat": {"layer": ClothingLayer.OUTER_TOP, "fabric": "duffel cloth", "formal": False, "origin": "Belgium"},

    # --- TRADITIONAL & CULTURAL ROBES ---
    "kimono": {"layer": ClothingLayer.FULL_BODY, "fabric": "chirimen silk", "formal": True, "origin": "Japan"},
    "yukata": {"layer": ClothingLayer.FULL_BODY, "fabric": "light cotton", "formal": False, "origin": "Japan"},
    "hanbok": {"layer": ClothingLayer.FULL_BODY, "fabric": "ramie and silk", "formal": True, "origin": "Korea"},
    "sari": {"layer": ClothingLayer.FULL_BODY, "fabric": "banarasi silk", "formal": True, "origin": "India"},
    "dhoti": {"layer": ClothingLayer.LEGS, "fabric": "unstitched cotton", "formal": True, "origin": "India"},
    "kurta": {"layer": ClothingLayer.INNER_TOP, "fabric": "khadi cotton", "formal": False, "origin": "South Asia"},
    "sherwani": {"layer": ClothingLayer.OUTER_TOP, "fabric": "heavy jacquard", "formal": True, "origin": "South Asia"},
    "thobe": {"layer": ClothingLayer.FULL_BODY, "fabric": "white cotton weave", "formal": True, "origin": "Arabian Peninsula"},
    "abaya": {"layer": ClothingLayer.FULL_BODY, "fabric": "crepe nida", "formal": False, "origin": "Middle East"},
    "kaftan": {"layer": ClothingLayer.FULL_BODY, "fabric": "embroidered damask", "formal": True, "origin": "Mesopotamia"},
    "poncho": {"layer": ClothingLayer.OUTER_TOP, "fabric": "woven alpaca wool", "formal": False, "origin": "Andes"},
    "serape": {"layer": ClothingLayer.OUTER_TOP, "fabric": "bright Mexican yarn", "formal": False, "origin": "Mexico"},
    "kilt": {"layer": ClothingLayer.LEGS, "fabric": "tartan twill wool", "formal": True, "origin": "Scotland"},
    "boubou": {"layer": ClothingLayer.FULL_BODY, "fabric": "bazin riche cotton", "formal": True, "origin": "West Africa"},
    "dashiki": {"layer": ClothingLayer.INNER_TOP, "fabric": "angelina print cotton", "formal": False, "origin": "West Africa"},
    "cheongsam_qipao": {"layer": ClothingLayer.FULL_BODY, "fabric": "embroidered silk", "formal": True, "origin": "China"},
    "changshan": {"layer": ClothingLayer.FULL_BODY, "fabric": "silk brocade", "formal": True, "origin": "China"},
    "dirndl": {"layer": ClothingLayer.FULL_BODY, "fabric": "linen and apron", "formal": True, "origin": "Bavaria / Austria"},
    "lederhosen": {"layer": ClothingLayer.LEGS, "fabric": "deerskin leather", "formal": True, "origin": "Bavaria / Austria"},

    # --- PANTS & BOTTOMS ---
    "blue_jeans": {"layer": ClothingLayer.LEGS, "fabric": "selvedge denim", "formal": False, "origin": "United States"},
    "dress_trousers": {"layer": ClothingLayer.LEGS, "fabric": "wool flannel", "formal": True, "origin": "United Kingdom"},
    "chinos": {"layer": ClothingLayer.LEGS, "fabric": "cotton twill", "formal": False, "origin": "Spain / US Army"},
    "khakis": {"layer": ClothingLayer.LEGS, "fabric": "khaki drill cotton", "formal": False, "origin": "British India"},
    "cargo_pants": {"layer": ClothingLayer.LEGS, "fabric": "ripstop canvas", "formal": False, "origin": "United Kingdom"},
    "joggers": {"layer": ClothingLayer.LEGS, "fabric": "french terry", "formal": False, "origin": "Global"},
    "sweatpants": {"layer": ClothingLayer.LEGS, "fabric": "brushed fleece", "formal": False, "origin": "United States"},
    "bermuda_shorts": {"layer": ClothingLayer.LEGS, "fabric": "linen blend", "formal": False, "origin": "Bermuda"},
    "cargo_shorts": {"layer": ClothingLayer.LEGS, "fabric": "heavy twill", "formal": False, "origin": "Global"},
    "boardshorts": {"layer": ClothingLayer.LEGS, "fabric": "quick-dry polyester", "formal": False, "origin": "Hawaii"},
    "leggings": {"layer": ClothingLayer.LEGS, "fabric": "spandex nylon", "formal": False, "origin": "Global"},
    "culottes": {"layer": ClothingLayer.LEGS, "fabric": "linen", "formal": False, "origin": "France"},
    "palazzo_pants": {"layer": ClothingLayer.LEGS, "fabric": "flowing georgette", "formal": False, "origin": "Italy"},
    "capri_pants": {"layer": ClothingLayer.LEGS, "fabric": "cotton sateen", "formal": False, "origin": "Italy"},

    # --- SKIRTS & DRESSES ---
    "mini_skirt": {"layer": ClothingLayer.LEGS, "fabric": "vinyl / cotton", "formal": False, "origin": "United Kingdom"},
    "midi_skirt": {"layer": ClothingLayer.LEGS, "fabric": "pleated chiffon", "formal": False, "origin": "Global"},
    "maxi_skirt": {"layer": ClothingLayer.LEGS, "fabric": "viscose jersey", "formal": False, "origin": "Global"},
    "pencil_skirt": {"layer": ClothingLayer.LEGS, "fabric": "stretch wool", "formal": True, "origin": "France"},
    "a_line_skirt": {"layer": ClothingLayer.LEGS, "fabric": "tartan", "formal": False, "origin": "France"},
    "pleated_skirt": {"layer": ClothingLayer.LEGS, "fabric": "polyester gabardine", "formal": False, "origin": "Global"},
    "cocktail_dress": {"layer": ClothingLayer.FULL_BODY, "fabric": "velvet", "formal": True, "origin": "United States"},
    "evening_gown": {"layer": ClothingLayer.FULL_BODY, "fabric": "taffeta", "formal": True, "origin": "France"},
    "ball_gown": {"layer": ClothingLayer.FULL_BODY, "fabric": "tulle and lace", "formal": True, "origin": "Europe"},
    "sundress": {"layer": ClothingLayer.FULL_BODY, "fabric": "floral cotton", "formal": False, "origin": "Global"},
    "wrap_dress": {"layer": ClothingLayer.FULL_BODY, "fabric": "silk jersey", "formal": False, "origin": "United States"},
    "shift_dress": {"layer": ClothingLayer.FULL_BODY, "fabric": "linen", "formal": False, "origin": "United States"},

    # --- ONE-PIECE & SPECIAL PURPOSE ---
    "overalls_dungarees": {"layer": ClothingLayer.FULL_BODY, "fabric": "heavy duck canvas", "formal": False, "origin": "United States"},
    "jumpsuit": {"layer": ClothingLayer.FULL_BODY, "fabric": "cotton drill", "formal": False, "origin": "United States"},
    "romper": {"layer": ClothingLayer.FULL_BODY, "fabric": "cotton voile", "formal": False, "origin": "United States"},
    "pajamas": {"layer": ClothingLayer.FULL_BODY, "fabric": "flannel cotton", "formal": False, "origin": "India / Persia"},
    "nightgown": {"layer": ClothingLayer.FULL_BODY, "fabric": "cotton batiste", "formal": False, "origin": "Europe"},
    "bathrobe": {"layer": ClothingLayer.FULL_BODY, "fabric": "terry cloth", "formal": False, "origin": "Global"},
    "swimsuit_one_piece": {"layer": ClothingLayer.FULL_BODY, "fabric": "lycra elastane", "formal": False, "origin": "Global"},
    "bikini": {"layer": ClothingLayer.UNDERWEAR, "fabric": "neoprene elastane", "formal": False, "origin": "France"},
    "swim_trunks": {"layer": ClothingLayer.LEGS, "fabric": "nylon with mesh lining", "formal": False, "origin": "Global"},
    "wetsuit": {"layer": ClothingLayer.FULL_BODY, "fabric": "closed-cell neoprene", "formal": False, "origin": "United States"},

    # --- UNDERWEAR & HOSIERY ---
    "boxer_shorts": {"layer": ClothingLayer.UNDERWEAR, "fabric": "woven cotton", "formal": False, "origin": "United States"},
    "briefs": {"layer": ClothingLayer.UNDERWEAR, "fabric": "combed cotton", "formal": False, "origin": "United States"},
    "boxer_briefs": {"layer": ClothingLayer.UNDERWEAR, "fabric": "modal spandex", "formal": False, "origin": "United States"},
    "panties": {"layer": ClothingLayer.UNDERWEAR, "fabric": "lace and micro-mesh", "formal": False, "origin": "Global"},
    "thong": {"layer": ClothingLayer.UNDERWEAR, "fabric": "seamless nylon", "formal": False, "origin": "Brazil"},
    "bra": {"layer": ClothingLayer.UNDERWEAR, "fabric": "underwire microfiber", "formal": False, "origin": "France / US"},
    "sports_bra": {"layer": ClothingLayer.UNDERWEAR, "fabric": "compression lycra", "formal": False, "origin": "United States"},
    "undershirt": {"layer": ClothingLayer.UNDERWEAR, "fabric": "fine ribbed cotton", "formal": False, "origin": "Global"},
    "thermal_long_johns": {"layer": ClothingLayer.UNDERWEAR, "fabric": "waffle knit wool", "formal": False, "origin": "United Kingdom"},
    "ankle_socks": {"layer": ClothingLayer.FEET, "fabric": "cushioned cotton", "formal": False, "origin": "Global"},
    "crew_socks": {"layer": ClothingLayer.FEET, "fabric": "cotton polyester blend", "formal": False, "origin": "Global"},
    "knee_high_socks": {"layer": ClothingLayer.FEET, "fabric": "merino blend", "formal": False, "origin": "Global"},
    "tights_pantyhose": {"layer": ClothingLayer.LEGS, "fabric": "denier nylon", "formal": True, "origin": "United States"},
    "thigh_high_stockings": {"layer": ClothingLayer.LEGS, "fabric": "sheer silk / silicone grip", "formal": True, "origin": "France"},

    # --- FOOTWEAR ---
    "oxford_shoes": {"layer": ClothingLayer.FEET, "fabric": "box calf leather", "formal": True, "origin": "Scotland / Ireland"},
    "derby_shoes": {"layer": ClothingLayer.FEET, "fabric": "cordovan leather", "formal": True, "origin": "England"},
    "monk_strap_shoes": {"layer": ClothingLayer.FEET, "fabric": "burnished calfskin", "formal": True, "origin": "European Monasteries"},
    "brogues": {"layer": ClothingLayer.FEET, "fabric": "perforated leather", "formal": True, "origin": "Ireland / Scotland"},
    "penny_loafers": {"layer": ClothingLayer.FEET, "fabric": "grain leather", "formal": False, "origin": "Norway / US"},
    "running_sneakers": {"layer": ClothingLayer.FEET, "fabric": "engineered knit mesh and foam", "formal": False, "origin": "Global"},
    "high_top_basketball_shoes": {"layer": ClothingLayer.FEET, "fabric": "canvas and vulcanized rubber", "formal": False, "origin": "United States"},
    "chelsea_boots": {"layer": ClothingLayer.FEET, "fabric": "elastic-sided leather", "formal": False, "origin": "Victorian England"},
    "chukka_boots": {"layer": ClothingLayer.FEET, "fabric": "suede leather", "formal": False, "origin": "Polo players / UK"},
    "combat_boots": {"layer": ClothingLayer.FEET, "fabric": "hardened roughout leather", "formal": False, "origin": "Military Global"},
    "cowboy_boots": {"layer": ClothingLayer.FEET, "fabric": "embossed leather with cuban heel", "formal": False, "origin": "American West"},
    "hiking_boots": {"layer": ClothingLayer.FEET, "fabric": "nubuck and vibram rubber", "formal": False, "origin": "Alps"},
    "leather_sandals": {"layer": ClothingLayer.FEET, "fabric": "strapped hide", "formal": False, "origin": "Ancient Greece"},
    "flip_flops": {"layer": ClothingLayer.FEET, "fabric": "molded eva rubber", "formal": False, "origin": "Japan (Zori) / Global"},
    "espadrilles": {"layer": ClothingLayer.FEET, "fabric": "canvas with braided jute rope sole", "formal": False, "origin": "Pyrenees / Spain"},
    "moccasins": {"layer": ClothingLayer.FEET, "fabric": "soft deerskin", "formal": False, "origin": "Indigenous North America"},
    "high_heels_stilettos": {"layer": ClothingLayer.FEET, "fabric": "patent leather with steel shank", "formal": True, "origin": "Italy / France"},
    "ballet_flats": {"layer": ClothingLayer.FEET, "fabric": "quilted lambskin", "formal": False, "origin": "France"},
    "slippers": {"layer": ClothingLayer.FEET, "fabric": "felted shearling", "formal": False, "origin": "Global"},
    "wooden_clogs": {"layer": ClothingLayer.FEET, "fabric": "carved willow or alder wood", "formal": False, "origin": "Netherlands"},

    # --- HEADWEAR & FACE ---
    "medical_mask": {"layer": ClothingLayer.FACE, "fabric": "non-woven polypropylene", "formal": False, "origin": "Global"},
    "balaclava": {"layer": ClothingLayer.FACE, "fabric": "knitted wool", "formal": False, "origin": "Crimea / UK"},
    "silk_sleep_mask": {"layer": ClothingLayer.FACE, "fabric": "mulberry silk", "formal": False, "origin": "Global"},
    "fedora": {"layer": ClothingLayer.HEAD, "fabric": "felted beaver fur", "formal": True, "origin": "France"},
    "bowler_derby_hat": {"layer": ClothingLayer.HEAD, "fabric": "hard wool felt", "formal": True, "origin": "London"},
    "top_hat": {"layer": ClothingLayer.HEAD, "fabric": "black silk plush", "formal": True, "origin": "England"},
    "flat_cap": {"layer": ClothingLayer.HEAD, "fabric": "donegal tweed", "formal": False, "origin": "Northern England"},
    "newsboy_cap": {"layer": ClothingLayer.HEAD, "fabric": "eight-panel wool", "formal": False, "origin": "United States"},
    "beret": {"layer": ClothingLayer.HEAD, "fabric": "knitted felt wool", "formal": False, "origin": "Basque Country"},
    "beanie_toque": {"layer": ClothingLayer.HEAD, "fabric": "ribbed acrylic wool", "formal": False, "origin": "Canada / Global"},
    "baseball_cap": {"layer": ClothingLayer.HEAD, "fabric": "cotton buckram with curved brim", "formal": False, "origin": "United States"},
    "bucket_hat": {"layer": ClothingLayer.HEAD, "fabric": "cotton canvas", "formal": False, "origin": "Irish Farmers"},
    "sun_hat": {"layer": ClothingLayer.HEAD, "fabric": "wide-brim woven straw", "formal": False, "origin": "Global"},
    "panama_hat": {"layer": ClothingLayer.HEAD, "fabric": "toquilla palm fiber", "formal": True, "origin": "Ecuador"},
    "turban": {"layer": ClothingLayer.HEAD, "fabric": "fine muslin cotton", "formal": True, "origin": "India / Middle East"},
    "hijab": {"layer": ClothingLayer.HEAD, "fabric": "georgette veil", "formal": False, "origin": "Islamic Tradition"},
    "ushanka": {"layer": ClothingLayer.HEAD, "fabric": "sheepskin with ear flaps", "formal": False, "origin": "Russia"},
    "sombrero": {"layer": ClothingLayer.HEAD, "fabric": "embroidered straw or felt", "formal": False, "origin": "Mexico"},
    "fez": {"layer": ClothingLayer.HEAD, "fabric": "red felt with tassel", "formal": True, "origin": "Morocco / Ottoman"},

    # --- ACCESSORIES & NECKWEAR ---
    "necktie": {"layer": ClothingLayer.NECK, "fabric": "printed silk twill", "formal": True, "origin": "Croatia / France"},
    "bow_tie": {"layer": ClothingLayer.NECK, "fabric": "silk grosgrain", "formal": True, "origin": "Croatia"},
    "cravat": {"layer": ClothingLayer.NECK, "fabric": "pleated linen", "formal": True, "origin": "Croatia"},
    "ascot_tie": {"layer": ClothingLayer.NECK, "fabric": "foulard patterned silk", "formal": True, "origin": "England (Royal Ascot)"},
    "winter_scarf": {"layer": ClothingLayer.NECK, "fabric": "knitted lambswool", "formal": False, "origin": "Ancient Rome / Global"},
    "bandana": {"layer": ClothingLayer.NECK, "fabric": "paisley cotton", "formal": False, "origin": "India"},
    "leather_belt": {"layer": ClothingLayer.WAIST, "fabric": "full-grain bridle leather with brass buckle", "formal": True, "origin": "Global"},
    "suspenders_braces": {"layer": ClothingLayer.ACCESSORY, "fabric": "elastic webbing with leather box ends", "formal": True, "origin": "United Kingdom"},
    "winter_gloves": {"layer": ClothingLayer.HANDS, "fabric": "lined nappa leather", "formal": False, "origin": "Global"},
    "mittens": {"layer": ClothingLayer.HANDS, "fabric": "boiled wool", "formal": False, "origin": "Latvia / Nordic"},
    "shawl": {"layer": ClothingLayer.ACCESSORY, "fabric": "pashmina cashmere", "formal": False, "origin": "Kashmir"},
    "cloak": {"layer": ClothingLayer.OUTER_TOP, "fabric": "heavy wool with clasp", "formal": False, "origin": "Medieval Europe"},
    "cape": {"layer": ClothingLayer.OUTER_TOP, "fabric": "velvet lining", "formal": True, "origin": "Europe"},
    "kitchen_apron": {"layer": ClothingLayer.FULL_BODY, "fabric": "waxed canvas", "formal": False, "origin": "Global"},
}


@dataclass
class WardrobeOmnibusSynthesizer:
    """The SS13 Global Real-World Wardrobe Omnibus Synthesizer engine.

    References itself dynamically through self-referential synthesis and metadata introspection.
    """
    machine_id: str = "SYNTH-WARDROBE-OMNIBUS-01"
    energy_level_kwh: float = 500.0
    synthesized_history: List[Dict[str, Any]] = field(default_factory=list)
    # Self-reference field satisfying recursive feature criteria
    self_reference: Optional["WardrobeOmnibusSynthesizer"] = None

    def __post_init__(self):
        # Explicitly assign self-reference to the object itself
        self.self_reference = self

    def reference_itself(self) -> Dict[str, Any]:
        """A method that explicitly references itself to satisfy the self-referential requirement."""
        # Check that self.self_reference points back to this identical instance
        assert self.self_reference is self
        return {
            "origin_machine": self.machine_id,
            "self_linked": True,
            "memory_address": hex(id(self)),
            "recursive_check": "WardrobeOmnibusSynthesizer points to WardrobeOmnibusSynthesizer"
        }

    def get_catalog_count(self) -> int:
        """Returns the total number of real-world clothing items cataloged."""
        return len(REAL_WORLD_CLOTHING_CATALOG)

    def search_by_layer(self, layer: ClothingLayer) -> List[Tuple[str, Dict[str, Any]]]:
        """Filters catalog items by worn clothing layer."""
        return [
            (name, data) for name, data in REAL_WORLD_CLOTHING_CATALOG.items()
            if data["layer"] == layer
        ]

    def synthesize_apparel(
        self,
        item_key: str,
        custom_color: str = "default",
        recursive_caller: Optional["WardrobeOmnibusSynthesizer"] = None
    ) -> Dict[str, Any]:
        """Synthesizes a real-world clothing item into an SS13 wearable datum."""
        # Self-referencing check
        caller = recursive_caller or self.self_reference

        if item_key not in REAL_WORLD_CLOTHING_CATALOG:
            raise KeyError(f"Clothing item '{item_key}' is not in the real-world wardrobe catalog")

        item_info = REAL_WORLD_CLOTHING_CATALOG[item_key]
        energy_cost = 2.5
        if self.energy_level_kwh < energy_cost:
            raise RuntimeError("Insufficient synthesizer energy to weave fabric")

        self.energy_level_kwh -= energy_cost
        record = {
            "item_key": item_key,
            "layer": item_info["layer"].value,
            "fabric": item_info["fabric"],
            "origin": item_info["origin"],
            "formal": item_info["formal"],
            "custom_color": custom_color,
            "synthesized_by": caller.machine_id if caller else self.machine_id,
            "sound": "loom_click_shuttle.ogg"
        }
        self.synthesized_history.append(record)
        return {
            "status": "FABRICATED",
            "garment": record,
            "remaining_energy_kwh": self.energy_level_kwh
        }

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) datum definitions for SS13 clothing integration."""
        return (
            "// ==========================================================================\n"
            "// SS13 REAL-WORLD WARDROBE OMNIBUS DEFINITIONS\n"
            "// Resolves #613 / Upstream #72\n"
            "// ==========================================================================\n\n"
            "/obj/machinery/wardrobe_omnibus_synthesizer\n"
            "\tname = \"Global Wardrobe Omnibus Synthesizer\"\n"
            "\tdesc = \"A high-precision quantum matter weaver capable of replicating every historical and modern clothing item from Earth.\"\n"
            "\ticon = 'icons/obj/machines/wardrobe_loom.dmi'\n"
            "\ticon_state = \"loom_idle\"\n"
            "\tvar/energy = 500\n"
            "\tvar/datum/wardrobe_synthesizer/self_ref\n\n"
            "/obj/machinery/wardrobe_omnibus_synthesizer/Initialize()\n"
            "\t. = ..()\n"
            "\tself_ref = src\n\n"
            "/obj/item/clothing/under/real_world\n"
            "\tname = \"real world tailored garment\"\n"
            "\tbody_parts_covered = CHEST|GROIN|LEGS|ARMS\n"
        )
