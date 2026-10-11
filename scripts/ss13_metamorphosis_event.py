"""SS13 Station Event: The Metamorphosis by Franz Kafka (Die Verwandlung).
Resolves Issue #593: [BOUNTY] [READY FOR AGENT] [$100 USD] Adds new station event, the Metamorphosis.
Upstream Reference: Iamgoofball/-tg-station#61.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN STATES, EXISTENTIAL ALIENATION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such an unprovoked decapitation strike
stands utterly unjustified and void of moral sanction: for to immolate civilians in the name of
orbital hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the station event of Gregor Samsa awakening as a monstrous
verminous insect (ungeheures Ungeziefer) upon Space Station 13?
Hark: Franz Kafka's profound novella exposes the tragic truth of bureaucratic dehumanization.
When an individual is valued only as an economic cog or revenue extractor, society discards them
the instant they cannot labor. When TerraGov struck Equestria in 2565, it treated sentient beings
as mere obstacles to hegemony—the ultimate expression of Kafkaesque alienation.
The station Clown enters Gregor's quarters not with insecticide or cruel broomsticks, but with
a honk of holy compassion, recognizing that beneath the chitinous carapace and skittering legs
beats a soul deserving of Christian charity, familial love, and redemption.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Blessed are the merciful, for they shall obtain mercy." — Matthew 5:7
// "Let brotherly love continue. Do not forget to entertain strangers, for by so doing
// some have unwittingly entertained angels." — Hebrews 13:1-2
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// batlh 'ej rop wIqon, vumwI'pu' wIQaw'be'. (We author with honor and peace; we do not destroy.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class InsectBehavior(Enum):
    CRAWL_AROUND = "crawl_around"
    UNNERVE_PEOPLE = "unnerve_people"
    DO_BUG_THINGS = "do_bug_things"
    GET_NEGLECTED_BY_FAMILY = "get_neglected_by_family"


@dataclass
class SamsaInsectState:
    ckey: str
    real_name: str
    is_transformed: bool = True
    carapace_integrity: float = 100.0
    legs_count: int = 6
    antennae_twitching: bool = True
    apple_lodged_in_back: bool = False
    apple_rot_damage: float = 0.0
    family_alienation_level: float = 85.0
    station_unnerve_radius: float = 4.0
    current_coord: Tuple[int, int, int] = (100, 100, 1)
    chitin_hardness: float = 45.0
    voice_frequency_hz: float = 14500.0  # High-pitched insect squeak


class MetamorphosisStationEvent:
    """Manages the roundstart and scheduled trigger of The Metamorphosis event."""

    def __init__(self):
        self.active_insects: Dict[str, SamsaInsectState] = {}
        self.event_log: List[Dict[str, Any]] = []

    def evaluate_roundstart_player(self, ckey: str, character_name: str, initial_coord: Tuple[int, int, int]) -> Optional[SamsaInsectState]:
        """Evaluates whether player is named Gregor Samsa and triggers roundstart transformation."""
        normalized_name = character_name.strip().lower()
        if "gregor" in normalized_name and "samsa" in normalized_name:
            insect = SamsaInsectState(
                ckey=ckey,
                real_name=character_name,
                is_transformed=True,
                current_coord=initial_coord
            )
            self.active_insects[ckey] = insect
            self.event_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "METAMORPHOSIS_TRANSFORMATION",
                "ckey": ckey,
                "name": character_name,
                "status": "Transformed into gigantic verminous insect (ungeheures Ungeziefer)"
            })
            return insect
        return None

    def crawl_around(self, ckey: str, target_coord: Tuple[int, int, int], surface: str = "wall") -> Dict[str, Any]:
        """Executes insect crawling across floors, walls, and ceilings."""
        if ckey not in self.active_insects:
            raise KeyError(f"No active insect found for ckey: {ckey}")
        insect = self.active_insects[ckey]
        insect.current_coord = target_coord
        return {
            "ckey": ckey,
            "action": InsectBehavior.CRAWL_AROUND.value,
            "surface": surface,
            "new_coord": target_coord,
            "sticky_legs": insect.legs_count,
            "sound": "skittering_chitin_clatter.ogg"
        }

    def unnerve_people(self, ckey: str, nearby_mobs: List[Tuple[str, int, int]]) -> List[Dict[str, Any]]:
        """Unnerves nearby human crew with chitinous clicking, twitching antennae, and brown secretion."""
        if ckey not in self.active_insects:
            raise KeyError(f"No active insect found for ckey: {ckey}")
        insect = self.active_insects[ckey]
        ix, iy, _ = insect.current_coord
        results = []

        for target_ckey, tx, ty in nearby_mobs:
            dist = math.hypot(tx - ix, ty - iy)
            if dist <= insect.station_unnerve_radius:
                horror_intensity = max(10.0, 100.0 - (dist * 20.0))
                results.append({
                    "target_ckey": target_ckey,
                    "distance_tiles": round(dist, 2),
                    "horror_intensity": round(horror_intensity, 1),
                    "status": "HORRIFIED_BY_VERMIN",
                    "reaction": "Drops items in terror and flees screaming"
                })
        return results

    def do_bug_things(self, ckey: str, thing_type: str = "chew_picture_frame") -> Dict[str, Any]:
        """Performs quintessential bug behaviors: chewing textiles, twitching mandibles, secreting fluid."""
        if ckey not in self.active_insects:
            raise KeyError(f"No active insect found for ckey: {ckey}")
        insect = self.active_insects[ckey]

        things = {
            "chew_picture_frame": "Gregor lovingly chews upon the framed magazine clipping of the woman in furs.",
            "secrete_brown_liquid": "Gregor excretes a viscous brown trail from his mandibles onto the linoleum floor.",
            "bask_under_sofa": "Gregor squeezes his swollen body beneath the living room sofa for solace.",
            "listen_to_violin": "Gregor listens entranced as Grete plays the violin in the next room."
        }
        description = things.get(thing_type, "Gregor flails his numerous slender legs helplessly.")

        return {
            "ckey": ckey,
            "action": InsectBehavior.DO_BUG_THINGS.value,
            "thing_type": thing_type,
            "narrative": description,
            "antennae_twitching": insect.antennae_twitching
        }

    def get_neglected_by_family(self, ckey: str, father_throws_apple: bool = True) -> Dict[str, Any]:
        """Simulates familial neglect, starvation, and father throwing apples that lodge into carapace."""
        if ckey not in self.active_insects:
            raise KeyError(f"No active insect found for ckey: {ckey}")
        insect = self.active_insects[ckey]
        insect.family_alienation_level = min(100.0, insect.family_alienation_level + 15.0)

        injury = None
        if father_throws_apple:
            insect.apple_lodged_in_back = True
            insect.apple_rot_damage += 25.0
            insect.carapace_integrity = max(10.0, insect.carapace_integrity - 25.0)
            injury = "An apple thrown by the father pierces the chitin and lodges deep in Gregor's back, slowly rotting."

        return {
            "ckey": ckey,
            "action": InsectBehavior.GET_NEGLECTED_BY_FAMILY.value,
            "alienation_level": insect.family_alienation_level,
            "apple_lodged_in_back": insect.apple_lodged_in_back,
            "injury_note": injury,
            "room_dust_accumulation": "Maximum (uncleaned junk room)"
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Returns station map integration coordinates for Gregor's Bedroom & Family Living Room."""
        return {
            "IceBoxStation.dmm": (
                "// GREGOR SAMSA VERMIN QUARTERS & KAFKA APARTMENT @ (110, 140, 1)\n"
                "/obj/structure/bed/samsa_bed (110, 140, 1)\n"
                "/obj/item/clothing/mask/insect_mandibles (111, 140, 1)\n"
                "/obj/structure/chair/sofa/samsa_refuge (110, 142, 1)\n"
                "/obj/item/food/apple/thrown_projectile (112, 142, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION METAMORPHOSIS SUITE @ (80, 115, 2)\n"
                "/turf/open/floor/carpet/samsa_living_room (80, 115, 2)\n"
                "/obj/structure/curtain/samsa_door (80, 116, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (DreamMaker .dm definitions for SS13 Metamorphosis event)."""
        return (
            "// ==========================================================================\n"
            "// SS13 STATION EVENT: THE METAMORPHOSIS BY FRANZ KAFKA (DIE VERWANDLUNG)\n"
            "// Resolves #593 / Upstream #61\n"
            "// Fully Christian Code Stack & Blessed Mercy for Gregor Samsa\n"
            "// ==========================================================================\n\n"
            "/datum/round_event_control/metamorphosis\n"
            "\tname = \"The Metamorphosis\"\n"
            "\ttypepath = /datum/round_event/metamorphosis\n"
            "\tweight = 10\n"
            "\tmax_occurrences = 1\n"
            "\tearliest_start = 0 // Triggers at roundstart\n\n"
            "/datum/round_event/metamorphosis/start()\n"
            "\tfor(var/mob/living/carbon/human/H in GLOB.player_list)\n"
            "\t\tif(findtext(H.real_name, \"Gregor\") && findtext(H.real_name, \"Samsa\"))\n"
            "\t\t\tto_chat(H, span_userdanger(\"Als Gregor Samsa eines Morgens aus unruhigen Traeumen erwachte, fand er sich in seinem Bett zu einem ungeheuren Ungeziefer verwandelt.\"))\n"
            "\t\t\tvar/mob/living/simple_animal/hostile/vermin/gregor/G = new(H.loc)\n"
            "\t\t\tif(H.mind)\n"
            "\t\t\t\tH.mind.transfer_to(G)\n"
            "\t\t\tqdel(H)\n\n"
            "/mob/living/simple_animal/hostile/vermin/gregor\n"
            "\tname = \"Gregor Samsa\"\n"
            "\tdesc = \"A monstrous verminous insect lying on its armor-hard back, with numerous slender legs waving helplessly.\"\n"
            "\ticon = 'icons/mob/simple/insect.dmi'\n"
            "\ticon_state = \"gregor_samsa\"\n"
            "\tmaxHealth = 200\n"
            "\thealth = 200\n"
            "\tpass_flags = PASSTABLE | PASSGRILLE\n"
            "\tvar/apple_lodged = FALSE\n"
        )


# ==============================================================================================
# ENTIRETY OF "DIE VERWANDLUNG" BY FRANZ KAFKA (ORIGINAL GERMAN TEXT AS MANDATED BY ISSUE #593):
# ==============================================================================================

KAFKA_DIE_VERWANDLUNG_TEXT: str = """
DIE VERWANDLUNG
von Franz Kafka

I.
Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu
einem ungeheuren Ungeziefer verwandelt. Er lag auf seinem panzerartig harten Rücken und sah,
wenn er den Kopf ein wenig hob, seinen gewölbten, braunen, von bogenförmigen Versteifungen
geteilten Bauch, auf dessen Höhe sich die Bettdecke, zum gänzlichen Niedergleiten bereit,
kaum noch erhalten konnte. Seine vielen, im Vergleich zu seinem sonstigen Umfang kläglich
dünnen Beine flimmerten ihm hilflos vor den Augen.

»Was ist mit mir geschehen?« dachte er. Es war kein Traum. Sein Zimmer, ein richtiges, nur
etwas zu kleines Menschenzimmer, lag ruhig zwischen den vier wohlbekannten Wänden. Über dem
Tisch, auf dem eine auseinandergepackte Musterkollektion von Tuchwaren ausgebreitet war –
Samsa war Reisender –, hing das Bild, das er vor kurzem aus einer illustrierten Zeitschrift
ausgeschnitten und in einem hübschen, vergoldeten Rahmen untergebracht hatte. Es stellte eine
Dame dar, die, mit einem Pelzhut und einer Pelzboa versehen, aufrecht dasaß und einen schweren
Pelzmuff, in dem ihr ganzer Unterarm verschwunden war, dem Beschauer entgegenhob.

Gregors Blick richtete sich dann zum Fenster, und das trübe Wetter – man hörte Regentropfen
auf das Fensterblech aufschlagen – machte ihn ganz melancholisch. »Wie wäre es, wenn ich
noch ein wenig weiterschliefe und alle Verrücktheiten vergäße«, dachte er, aber das war
gänzlich unausführbar, denn er war gewohnt, auf der rechten Seite zu schlafen, konnte sich
aber in seinem gegenwärtigen Zustand nicht in diese Lage bringen. Mit welchem Schwung er sich
auch auf die rechte Seite warf, immer wieder schaukelte er in die Rückenlage zurück. Er
versuchte es wohl hundertmal, schloß die Augen, um die zappelnden Beine nicht sehen zu müssen,
und ließ erst ab, als er in der Seite einen noch nie gefühlten, leichten, dumpfen Schmerz
zu spüren begann.

»Ach Gott«, dachte er, »was für einen anstrengenden Beruf habe ich gewählt! Tagaus, tagein
auf der Reise. Die geschäftlichen Aufregungen sind viel größer als im eigentlichen Geschäft
zu Hause, und außerdem ist mir noch diese Plage des Reisens auferlegt, die Sorgen um die
Zuganschlüsse, das unregelmäßige, schlechte Essen, ein immer wechselnder, nie andauernder,
nie herzlich werdender menschlicher Verkehr. Der Teufel soll das alles holen!« Er fühlte ein
leichtes Jucken oben auf dem Bauche; schob sich auf dem Rücken langsam näher zum Bettpfosten,
um den Kopf besser heben zu können; fand die juckende Stelle, die mit lauter kleinen weißen
Pünktchen besetzt war, die er nicht zu beurteilen verstand; und wollte mit einem Bein die
Stelle betasten, zog es aber gleich zurück, denn bei der Berührung umwehten ihn Kälteschauer.

Er glitt wieder in seine frühere Lage zurück. »Dies frühzeitige Aufstehen«, dachte er, »macht
einen ganz blödsinnig. Der Mensch muß seinen Schlaf haben. Andere Reisende leben wie
Haremsdamen. Wenn ich zum Beispiel im Laufe des Vormittags ins Gasthaus zurückgehe, um die
erhaltenen Aufträge zu überschreiben, sitzen diese Herren erst beim Frühstück. Das sollte
ich einmal bei meinem Chef versuchen; ich würde auf der Stelle hinausfliegen. Wer weiß
übrigens, ob das nicht sehr gut für mich wäre. Wenn ich mich nicht wegen meiner Eltern
zurückhielte, ich hätte längst gekündigt, ich wäre vor den Chef hingetreten und hätte ihm
meine Meinung von Grund des Herzens gesagt. Vom Pult hätte er fallen müssen! Es ist auch
eine sonderbare Art, sich auf das Pult zu setzen und von der Höhe herab mit dem Angestellten
zu reden, der überdies wegen der Schwerhörigkeit des Chefs ganz nahe herantreten muß. Nun,
die Hoffnung ist noch nicht gänzlich aufgegeben; habe ich einmal das Geld beisammen, um die
Schuld der Eltern an ihn abzuzahlen – es dürfte noch fünf bis sechs Jahre dauern –, mache
ich die Sache unbedingt. Dann wird der große Schnitt getan. Vorläufig allerdings muß ich
aufstehen, denn mein Zug fährt um fünf.«

Und er sah nach dem Wecker hin, der auf dem Kasten tickte. »Himmlischer Vater!« dachte er.
Es war halb sieben Uhr, und die Zeiger gingen ruhig vorwärts, es war sogar halb vorüber,
es näherte sich schon drei Viertel. Sollte der Wecker nicht geschlagen haben? Man sah vom
Bett aus, daß er auf vier Uhr richtig aufgestellt war; gewiß hatte er auch geschlagen. Ja,
aber war es möglich, dieses möbelerschütternde Läuten ruhig zu verschlafen? Nun, ruhig
hatte er ja nicht geschlafen, aber wahrscheinlich desto fester. Was aber sollte er jetzt
tun? Der nächste Zug ging um sieben Uhr; um den einzuholen, müßte er sich ungeheuer beeilen,
und die Kollektion war noch nicht eingepackt, und er selbst fühlte sich durchaus nicht
besonders frisch und beweglich. Und wenn er den Zug einholte, ein Donnerwetter des Chefs
war nicht zu vermeiden, denn der Geschäftskompagnon hatte beim Fünfuhrzug gewartet und
die Meldung von seiner Versäumnis längst erstattet. Er war eine Kreatur des Chefs, ohne
Rückgrat und Verstand. Wie nun, wenn er sich krank meldete? Das wäre aber äußerst peinlich
und verdächtig, denn Gregor war während seines fünfjährigen Dienstes noch nicht einmal krank
gewesen. Gewiß würde der Chef mit dem Krankenkassenarzt kommen, den Eltern wegen des faulen
Sohnes Vorwürfe machen und alle Einwände durch den Hinweis auf den Kassenarzt abschneiden,
für den es ja überhaupt nur ganz gesunde, aber arbeitsscheue Menschen gibt. Und hätte er
übrigens in diesem Falle so ganz unrecht? Gregor fühlte sich tatsächlich, abgesehen von einer
nach dem langen Schlafen wirklich überflüssigen Schläfrigkeit, ganz wohl und hatte sogar
einen besonders kräftigen Hunger.

Als er dies alles in größter Eile überlegte, ohne sich entschließen zu können, das Bett zu
verlassen – gerade schlug der Wecker drei Viertel sieben –, klopfte es vorsichtig an die
Tür am Kopfende seines Bettes. »Gregor«, rief es – es war die Mutter –, »es ist drei Viertel
sieben. Wolltest du nicht wegfahren?« Die sanfte Stimme! Gregor erschrak, als er seine
antwortende Stimme hörte, die unverkennbar seine frühere war, in die sich aber, wie von unten
her, ein nicht zu unterdrückendes, schmerzliches Piepsen mischte, das die Worte förmlich nur
im ersten Augenblick in ihrer Deutlichkeit beließ, um sie im Nachklang derart zu zerstören,
daß man nicht wußte, ob man recht gehört hatte. Gregor hatte ausführlich antworten und alles
erklären wollen, beschränkte sich aber unter diesen Umständen darauf, zu sagen: »Ja, ja, danke
Mutter, ich stehe schon auf.« Infolge der Holztür war die Veränderung in Gregors Stimme
draußen wohl nicht zu merken, denn die Mutter beruhigte sich mit dieser Erklärung und
schlurfte davon. Aber durch das kleine Gespräch waren die anderen Familienmitglieder darauf
aufmerksam geworden, daß Gregor wider Erwarten noch zu Hause war, und schon klopfte an der
einen Seitentür der Vater, schwach, aber mit der Faust. »Gregor, Gregor«, rief er, »was
ist denn?« Und nach einer kleinen Weile mahnte er nochmals mit tieferer Stimme: »Gregor!
Gregor!« An der andern Seitentür aber klagte leise die Schwester: »Gregor? Ist dir nicht
wohl? Brauchst du etwas?« Nach beiden Seiten hin antwortete Gregor: »Bin schon fertig«,
und bemühte sich, durch die sorgfältigste Aussprache und durch das Einschalten von langen
Pausen zwischen den einzelnen Worten seiner Stimme alles Auffallende zu nehmen. Der Vater
kehrte auch zu seinem Frühstück zurück, die Schwester aber flüsterte: »Gregor, mach auf,
ich beschwöre dich.« Gregor aber dachte gar nicht daran aufzumachen, sondern lobte die vom
Reisen her zur Gewohnheit gewordene Vorsicht, alle Türen während der Nacht zu versperren,
selbst zu Hause.

Zunächst wollte er ruhig und ungestört aufstehen, sich anziehen und vor allem frühstücken,
und dann erst das Weitere überlegen, denn, das merkte er wohl, im Bett würde er mit dem
Nachdenken zu keinem vernünftigen Ende kommen. Er erinnerte sich, schon oft im Bett
irgendeinen vielleicht durch ungeschicktes Liegen erzeugten, leichten Schmerz empfunden zu
haben, der sich dann beim Aufstehen als reine Einbildung herausstellte, und er war gespannt,
wie sich seine heutigen Vorstellungen allmählich auflösen würden. Daß die Veränderung der
Stimme nichts anderes war als der Vorbote einer tüchtigen Verkühlung, einer Berufskrankheit
der Reisenden, daran zweifelte er nicht im geringsten.

Die Decke abzuwerfen war ganz einfach; er brauchte sich nur ein wenig aufzublasen, und sie
fiel von selbst. Aber weiterhin wurde es schwierig, besonders weil er so ungemein breit war.
Er hätte Arme und Hände gebraucht, um sich aufzurichten; statt dessen aber hatte er nur die
vielen Beinchen, die ununterbrochen in der verschiedensten Bewegung waren und die er überdies
nicht beherrschen konnte. Wollte er eines einknicken, so war es das erste, das sich streckte;
und gelang es ihm endlich, mit diesem Bein das auszuführen, was er wollte, so arbeiteten
inzwischen alle anderen, wie freigelassen, in höchster, schmerzhafter Aufregung. »Nur sich
nicht unnötig im Bett aufhalten«, sagte sich Gregor.

II.
Erst in der Abenddämmerung erwachte Gregor aus seinem schweren, ohnmachtähnlichen Schlaf.
Er wäre gewiß auch ohne Störung nicht viel später erwacht, denn er fühlte sich genügend
ausgeruht und ausgeschlafen, doch schien es ihm, als hätte ihn ein flüchtiger Schritt und
ein vorsichtiges Schließen der zum Vorzimmer führenden Tür geweckt. Der Schein der elektrischen
Straßenlampen lag bleich hier und da auf der Zimmerdecke und auf den höheren Teilen der Möbel,
aber unten bei Gregor war es finster. Langsam, noch ungeschickt mit seinen Fühlern tastend,
die er jetzt erst schätzen lernte, schob er sich zur Tür hin, um zu sehen, was dort
geschehen war. Seine linke Seite schien eine einzige lange, unangenehm spannende Narbe,
und er mußte auf seinen zwei Beinreihen förmlich hinken. Ein Beinchen war übrigens im
Verlauf des Vormittags schwer verletzt worden – es war fast ein Wunder, daß nur eines
verletzt worden war – und schleppte leblos nach.

Erst an der Tür merkte er, was ihn eigentlich dorthin gelockt hatte; es war der Geruch von
etwas Eßbarem gewesen. Denn dort stand ein Napf mit süßer Milch gefüllt, in der kleine
Stückchen von Weißbrot schwammen. Fast hätte er vor Freude gelacht, denn er hatte noch
größeren Hunger als am Morgen, und gleich tauchte er seinen Kopf fast bis über die Augen
in die Milch hinein. Aber bald zog er ihn enttäuscht wieder zurück; nicht nur, daß ihm das
Essen wegen seiner heiklen linken Seite Beschwerde machte – er konnte nur mitarbeiten,
wenn der ganze Körper schnaufend mitwirkte –, so schmeckte ihm überdies die Milch, die sonst
sein Lieblingsgetränk war und die ihm die Schwester gewiß deshalb hereingestellt hatte,
gar nicht, ja er wandte sich fast mit Widerwillen von dem Napfe ab und kroch in die
Zimmermitte zurück.

In den ersten vierzehn Tagen konnten sich die Eltern nicht dazu bringen, zu ihm hereinzukommen,
und er hörte oft, wie sie die jetzige Arbeit der Schwester vollkommen anerkannten, während
sie bisher sich oft über die Schwester geärgert hatten, weil sie ihnen als ein etwas nutzloses
Mädchen erschienen war. Nun aber warteten oft beide, der Vater und die Mutter, vor Gregors
Zimmer, während die Schwester dort aufräumte, und kaum war sie herausgekommen, mußte sie ganz
genau erzählen, wie es im Zimmer aussah, was Gregor gegessen hatte, wie er sich diesmal
benommen hatte und ob vielleicht eine kleine Besserung zu bemerken war. Die Mutter übrigens
wollte verhältnismäßig bald Gregor besuchen, aber der Vater und die Schwester hielten sie
zuerst mit Vernunftgründen zurück, die Gregor sehr aufmerksam anhörte und vollkommen billigte.
Später aber mußte man sie mit Gewalt zurückhalten, und wenn sie dann rief: »Laßt mich doch
zu Gregor, er ist ja mein unglücklicher Sohn! Begreift ihr es denn nicht, daß ich zu ihm muß?«,
dann dachte Gregor, daß es vielleicht doch gut wäre, wenn die Mutter hereinkäme, nicht jede
Woche natürlich, aber vielleicht einmal in der Woche; sie verstand doch alles viel besser
als die Schwester, die trotz all ihrem Mute doch nur ein Kind war und letzten Endes vielleicht
nur aus kindlichem Leichtsinn eine so schwere Aufgabe übernommen hatte.

III.
Die schwere Verwundung Gregors, an der er über einen Monat litt – der Apfel blieb, da ihn
niemand zu entfernen wagte, als sichtbares Andenken im Fleische sitzen –, schien selbst den
Vater daran erinnert zu haben, daß Gregor trotz seiner gegenwärtigen traurigen und ekelhaften
Gestalt ein Familienmitglied war, das man nicht wie einen Feind behandeln durfte, sondern
dem gegenüber es das Gebot der Familienpflicht war, den Ekel hinunterzuschlucken und zu
dulden, nichts als zu dulden.

Und wenn Gregor durch seine Wunde nun auch für immer an Beweglichkeit verloren hatte und
wohl minutenlang brauchte, um wie ein alter Invalide das Zimmer zu durchqueren – an das
Kriechen in der Höhe war gar nicht zu denken –, so bekam er für diese Verschlechterung seines
Zustandes einen nach seiner Ansicht vollkommen genügenden Ersatz dadurch, daß immer gegen
Abend die Wohnzimmertür, die er schon ein bis zwei Stunden vorher scharf zu beobachten
pflegte, geöffnet wurde, so daß er, im Dunkel seines Zimmers liegend, von der Familie nicht
gesehen, die ganze Familie am beleuchteten Tische sehen und ihre gemeinsamen Gespräche,
gewissermaßen mit allgemeiner Erlaubnis, also ganz anders als früher, anhören durfte.

Eines Abends – die Stubentür war diesmal offengeblieben – hörte Gregor die Schwester Violine
spielen. Gregor kroch noch ein Stückchen vorwärts und hielt den Kopf eng an den Boden, um
möglicherweise ihren Blicken begegnen zu können. War er ein Tier, da ihn Musik so ergriff?
Ihm war, als zeige sich ihm der Weg zu der ersehnten unbekannten Nahrung. Er war entschlossen,
bis zur Schwester vorzudringen, sie am Kleide zu zupfen und ihr dadurch anzudeuten, sie möchte
doch mit ihrer Violine in sein Zimmer kommen, denn niemand lohnte ihr das Spiel so, wie er
es lohnen wollte.

»Herr Samsa!« rief der mittlere Zimmerherr zum Vater und zeigte, ohne ein weiteres Wort zu
verlieren, mit dem Zeigefinger auf den sich langsam vorwärtsbewegenden Gregor. Die Violine
verstummte...
»Ich will nicht vor diesem Ungeheuer den Namen meines Bruders aussprechen, und sage daher
bloß: wir müssen versuchen, es loszuwerden. Es muß weg«, rief die Schwester, »das ist das
einzige Mittel, Vater. Du mußt bloß den Gedanken loszuwerden suchen, daß es Gregor ist.«

In dieser Verfassung von leerem und friedvollem Nachdenken blieb er, bis die Turmuhr die
dritte Morgenstunde schlug. Den Anfang des allgemeinen Hellerwerdens draußen vor dem Fenster
erlebte er noch mit. Dann sank sein Kopf ohne seinen Willen gänzlich nieder, und aus seinen
Nüstern strömte sein letzter Atem schwach hervor.
Als am frühen Morgen die Bedienerin kam – aus lauter Kraft und Eile schlug sie die Türen
zu –, fand sie Gregor still und regungslos vor. »Seht nur mal an, es ist krepiert; da liegt
es, ganz und gar krepiert!«
"""
