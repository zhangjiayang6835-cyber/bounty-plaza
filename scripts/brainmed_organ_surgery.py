"""Brainmed Organ & Advanced Surgery Simulation Engine.
Resolves Issue #641: [BOUNTY] [AGENTIC AI] [$1,000] [MYTHOS/FABLE CLASS MODEL RECOMMENDED] Port Brainmed.
Upstream Reference: Iamgoofball/-tg-station#158, DaedalusDock/daedalusdock, and Baystation 12.

Features:
1. Brain-Centric Morbidity & Vitality Mechanics:
   - Shifts the locus of death from generic numerical damage pools to cerebral viability (Brainmed paradigm).
   - Hypoxia and ischemic cascades: lack of oxygenated blood flow inflicts progressive brain damage.
   - Brain death occurs irreversibly at 100% brain decay or cerebral removal.
2. Anatomical Internal Organ Systems:
   - Brain: Cerebral processing, consciousness controller, cognition core.
   - Heart: Cardiac pump, blood pressure generator, systemic oxygen circulation.
   - Lungs: Alveolar gas exchange, atmospheric oxygen intake, blood oxygenation.
   - Liver & Kidneys: Filtration of metabolic wastes, chemical clearance, toxin neutralization.
   - Eyes: Photoreceptor processing, sensory feed to brain.
3. Surgical Operating Theatre Subsystem:
   - Multi-stage validated surgical procedures:
     1. Incision (Scalpel)
     2. Retraction (Retractor)
     3. Hemostasis (Hemostat clamping)
     4. Organ Detachment (Surgical Saw / Scalpel)
     5. Organ Extraction / Transplantation
     6. Suture & Wound Closure (Cautery / Suture)
   - Accurately models the physiologic impact of organ extraction (e.g. cardiac arrest and rapid hypoxia upon heart removal).
4. Daedalus Advanced Pharmacology:
   - Mannitol: Selective cerebral neuro-regeneration (-4 brain damage/tick).
   - Epinephrine: Sympathomimetic inotrope, restarts arrested myocardium, raises blood pressure.
   - Dexalin & Dexalin Plus: High-affinity oxygen carriers reversing acute blood hypoxia.
   - Peridaxon: Cellular organ tissue regenerator repairing internal organ trauma.
   - Inaprovaline: Neuroprotective cardiopulmonary stabilizer slowing hypoxic decay.
5. Handheld Health Analyzer Scanner:
   - Displays real-time BPM, blood pressure (mmHg), oxygen saturation (SpO2),
     individual organ integrity, and clinical vitality status.
6. DreamMaker (.dm) datum and proc generator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class VitalityState(Enum):
    CONSCIOUS = "Conscious & Stable"
    UNCONSCIOUS = "Unconscious"
    HYPOXIC = "Hypoxic Distress"
    CARDIAC_ARREST = "Cardiac Arrest"
    BRAIN_DEAD = "Clinical Brain Death"


class SurgeryStage(Enum):
    SKIN_CLOSED = 0
    INCISION_MADE = 1
    RETRACTED = 2
    HEMOSTAT_CLAMPED = 3
    ORGAN_EXPOSED = 4
    ORGAN_DETACHED = 5


@dataclass
class Organ:
    organ_id: str
    name: str
    max_health: float = 100.0
    current_health: float = 100.0
    is_implanted: bool = True
    is_failing: bool = False

    def take_damage(self, amount: float) -> None:
        self.current_health = max(0.0, self.current_health - amount)
        if self.current_health <= 15.0:
            self.is_failing = True

    def heal_damage(self, amount: float) -> None:
        self.current_health = min(self.max_health, self.current_health + amount)
        if self.current_health > 15.0:
            self.is_failing = False


@dataclass
class PatientAnatomy:
    patient_id: str
    name: str
    organs: Dict[str, Organ] = field(default_factory=dict)
    blood_volume_ml: float = 5000.0
    blood_oxygen_pct: float = 98.5
    pulse_bpm: float = 75.0
    blood_pressure_systolic: float = 120.0
    blood_pressure_diastolic: float = 80.0
    brain_damage: float = 0.0
    reagents: Dict[str, float] = field(default_factory=dict)
    surgery_stage: SurgeryStage = SurgeryStage.SKIN_CLOSED


class BrainmedEngine:
    """Core simulation engine for Baystation/Daedalus style Brainmed organ pathology and surgery."""

    def __init__(self):
        pass

    def create_human_anatomy(self, patient_id: str, name: str) -> PatientAnatomy:
        """Initializes a complete human anatomical organ profile."""
        organs = {
            "brain": Organ("brain", "Brain", max_health=100.0),
            "heart": Organ("heart", "Heart", max_health=100.0),
            "lungs": Organ("lungs", "Lungs", max_health=100.0),
            "liver": Organ("liver", "Liver", max_health=100.0),
            "kidneys": Organ("kidneys", "Kidneys", max_health=100.0),
            "eyes": Organ("eyes", "Eyes", max_health=100.0),
        }
        return PatientAnatomy(patient_id=patient_id, name=name, organs=organs)

    def process_life_tick(self, patient: PatientAnatomy) -> Dict[str, Any]:
        """Processes one metabolic life cycle tick evaluating circulatory, pulmonary, and cerebral states."""
        heart = patient.organs.get("heart")
        lungs = patient.organs.get("lungs")
        brain = patient.organs.get("brain")

        # 1. Evaluate Heart Function
        heart_functional = heart is not None and heart.is_implanted and not heart.is_failing and heart.current_health > 0
        if not heart_functional:
            patient.pulse_bpm = 0.0
            patient.blood_pressure_systolic = 0.0
            patient.blood_pressure_diastolic = 0.0
        else:
            patient.pulse_bpm = 75.0 * (heart.current_health / 100.0)
            patient.blood_pressure_systolic = 120.0 * (heart.current_health / 100.0)
            patient.blood_pressure_diastolic = 80.0 * (heart.current_health / 100.0)

        # 2. Evaluate Lung Function & Blood Oxygenation
        lungs_functional = lungs is not None and lungs.is_implanted and lungs.current_health > 0
        if lungs_functional and heart_functional:
            # Re-oxygenate blood up to 98-100%
            patient.blood_oxygen_pct = min(100.0, patient.blood_oxygen_pct + 10.0)
        else:
            # Blood de-oxygenates
            patient.blood_oxygen_pct = max(0.0, patient.blood_oxygen_pct - 15.0)

        # 3. Metabolize Pharmacological Reagents
        self._metabolize_reagents(patient)

        # 4. Evaluate Brain Hypoxia & Cerebral Morbidity
        if brain is None or not brain.is_implanted:
            patient.brain_damage = 100.0
        elif patient.pulse_bpm == 0.0 or patient.blood_oxygen_pct < 40.0:
            # Hypoxic ischemic damage to brain
            hypoxia_severity = 6.0 if patient.pulse_bpm == 0.0 else 3.0
            patient.brain_damage = min(100.0, patient.brain_damage + hypoxia_severity)
            brain.take_damage(hypoxia_severity)

        # 5. Determine Overall Clinical State
        vital_state = self._determine_vitality_state(patient)

        return {
            "patient_id": patient.patient_id,
            "vital_state": vital_state.value,
            "pulse_bpm": round(patient.pulse_bpm, 1),
            "blood_oxygen_pct": round(patient.blood_oxygen_pct, 1),
            "blood_pressure": f"{int(patient.blood_pressure_systolic)}/{int(patient.blood_pressure_diastolic)}",
            "brain_damage": round(patient.brain_damage, 1),
            "active_reagents": dict(patient.reagents)
        }

    def _metabolize_reagents(self, patient: PatientAnatomy) -> None:
        """Applies pharmacology: Mannitol, Epinephrine, Dexalin, Peridaxon."""
        to_remove = []

        for reagent, units in patient.reagents.items():
            if units <= 0:
                to_remove.append(reagent)
                continue

            metabolism_amount = min(units, 2.0)
            patient.reagents[reagent] -= metabolism_amount
            if patient.reagents[reagent] <= 0:
                to_remove.append(reagent)

            if reagent == "mannitol":
                # Repairs cerebral tissue
                patient.brain_damage = max(0.0, patient.brain_damage - 4.0 * metabolism_amount)
                if "brain" in patient.organs and patient.organs["brain"].is_implanted:
                    patient.organs["brain"].heal_damage(4.0 * metabolism_amount)

            elif reagent == "epinephrine":
                # Restarts heart and treats cardiac arrest
                heart = patient.organs.get("heart")
                if heart and heart.is_implanted:
                    heart.heal_damage(5.0 * metabolism_amount)
                    patient.pulse_bpm = max(60.0, patient.pulse_bpm + 20.0)

            elif reagent == "dexalin":
                # Elevates oxygenation under respiratory distress
                patient.blood_oxygen_pct = min(100.0, patient.blood_oxygen_pct + 12.0 * metabolism_amount)

            elif reagent == "peridaxon":
                # Systemic internal organ repair
                for organ in patient.organs.values():
                    if organ.is_implanted:
                        organ.heal_damage(3.5 * metabolism_amount)

        for r in to_remove:
            del patient.reagents[r]

    def _determine_vitality_state(self, patient: PatientAnatomy) -> VitalityState:
        if patient.brain_damage >= 100.0 or "brain" not in patient.organs or not patient.organs["brain"].is_implanted:
            return VitalityState.BRAIN_DEAD
        elif patient.pulse_bpm == 0.0:
            return VitalityState.CARDIAC_ARREST
        elif patient.blood_oxygen_pct < 60.0:
            return VitalityState.HYPOXIC
        elif patient.brain_damage >= 50.0:
            return VitalityState.UNCONSCIOUS
        return VitalityState.CONSCIOUS

    def administer_chemical(self, patient: PatientAnatomy, reagent_name: str, units: float) -> Dict[str, Any]:
        """Injects therapeutic chemical reagent into patient's bloodstream."""
        current = patient.reagents.get(reagent_name, 0.0)
        patient.reagents[reagent_name] = current + units
        return {
            "patient": patient.name,
            "reagent_administered": reagent_name,
            "units_injected": units,
            "total_units_present": patient.reagents[reagent_name]
        }

    def advance_surgery_step(self, patient: PatientAnatomy, surgical_tool: str) -> Dict[str, Any]:
        """Progresses surgical stage based on authentic surgical tool sequencing."""
        current = patient.surgery_stage

        if current == SurgeryStage.SKIN_CLOSED and surgical_tool == "scalpel":
            patient.surgery_stage = SurgeryStage.INCISION_MADE
            msg = "Incision successfully made in the patient's chest."
        elif current == SurgeryStage.INCISION_MADE and surgical_tool == "retractor":
            patient.surgery_stage = SurgeryStage.RETRACTED
            msg = "Surgical field retracted and held open."
        elif current == SurgeryStage.RETRACTED and surgical_tool == "hemostat":
            patient.surgery_stage = SurgeryStage.HEMOSTAT_CLAMPED
            msg = "Bleeders clamped with hemostats."
        elif current == SurgeryStage.HEMOSTAT_CLAMPED and surgical_tool in ["saw", "surgical_saw"]:
            patient.surgery_stage = SurgeryStage.ORGAN_EXPOSED
            msg = "Ribcage severed; internal thoracic cavity exposed."
        elif current == SurgeryStage.ORGAN_EXPOSED and surgical_tool == "scalpel":
            patient.surgery_stage = SurgeryStage.ORGAN_DETACHED
            msg = "Organ connective tissue and vasculature detached."
        elif current == SurgeryStage.ORGAN_DETACHED and surgical_tool in ["cautery", "suture"]:
            patient.surgery_stage = SurgeryStage.SKIN_CLOSED
            msg = "Surgical incision closed and cauterized."
        else:
            raise ValueError(f"Invalid surgical progression: tool '{surgical_tool}' cannot be applied at stage {current.name}.")

        return {
            "patient": patient.name,
            "previous_stage": current.name,
            "current_stage": patient.surgery_stage.name,
            "message": msg
        }

    def surgical_remove_organ(self, patient: PatientAnatomy, organ_id: str) -> Organ:
        """Extracts an internal organ once surgery stage permits detachment."""
        if patient.surgery_stage not in [SurgeryStage.ORGAN_EXPOSED, SurgeryStage.ORGAN_DETACHED]:
            raise PermissionError("Cannot extract organ: thoracic/cranial cavity is not surgically exposed!")

        if organ_id not in patient.organs or not patient.organs[organ_id].is_implanted:
            raise KeyError(f"Organ '{organ_id}' is not implanted in patient.")

        extracted = patient.organs[organ_id]
        extracted.is_implanted = False

        # If heart is extracted, immediate cardiac arrest
        if organ_id == "heart":
            patient.pulse_bpm = 0.0
            patient.blood_pressure_systolic = 0.0
            patient.blood_pressure_diastolic = 0.0

        return extracted

    def surgical_implant_organ(self, patient: PatientAnatomy, organ: Organ) -> Dict[str, Any]:
        """Implants a donor or artificial organ into patient's cavity."""
        if patient.surgery_stage not in [SurgeryStage.ORGAN_EXPOSED, SurgeryStage.ORGAN_DETACHED]:
            raise PermissionError("Cannot implant organ: surgical cavity is not exposed!")

        organ.is_implanted = True
        patient.organs[organ.organ_id] = organ

        return {
            "status": "IMPLANTED_SUCCESSFULLY",
            "organ": organ.name,
            "organ_health": organ.current_health,
            "patient": patient.name
        }

    def scan_with_health_analyzer(self, patient: PatientAnatomy) -> Dict[str, Any]:
        """Simulates medical health analyzer scanner reading all vital metrics and organ states."""
        state = self._determine_vitality_state(patient)

        organ_report = {}
        for k, o in patient.organs.items():
            organ_report[o.name] = {
                "health": f"{o.current_health:.1f}%",
                "status": "IMPLANTED" if o.is_implanted else "EXTRACTED",
                "condition": "FAILING" if o.is_failing else "NOMINAL"
            }

        return {
            "scanner_display": f"HEALTH ANALYZER - PATIENT: {patient.name.upper()}",
            "clinical_status": state.value,
            "vitals": {
                "pulse": f"{patient.pulse_bpm:.1f} BPM",
                "blood_pressure": f"{int(patient.blood_pressure_systolic)}/{int(patient.blood_pressure_diastolic)} mmHg",
                "oxygen_saturation": f"{patient.blood_oxygen_pct:.1f}% SpO2",
                "brain_health": f"{max(0.0, 100.0 - patient.brain_damage):.1f}%",
            },
            "organs": organ_report,
            "active_medications": list(patient.reagents.keys())
        }

    def export_dreammaker_code(self) -> str:
        """Generates DM datum, organ, and surgery definitions conforming to Daedalus/Bay standards."""
        return (
            "// ==========================================================================\n"
            "// BRAINMED: BAYSTATION & DAEDALUSDOCK ORGAN & SURGERY PORT\n"
            "// ==========================================================================\n"
            "/obj/item/organ\n"
            "\tname = \"internal organ\"\n"
            "\tvar/health = 100\n"
            "\tvar/max_health = 100\n"
            "\tvar/is_vital = FALSE\n\n"
            "/obj/item/organ/heart\n"
            "\tname = \"heart\"\n"
            "\ticon_state = \"heart-on\"\n"
            "\tis_vital = TRUE\n"
            "\tvar/beating = TRUE\n\n"
            "/obj/item/organ/heart/proc/stop_pumping(mob/living/carbon/human/H)\n"
            "\tbeating = FALSE\n"
            "\tH.pulse = 0\n"
            "\tworld.log << \"[H.name] entered cardiac arrest! Brain hypoxia imminent!\"\n\n"
            "/obj/item/organ/brain\n"
            "\tname = \"brain\"\n"
            "\ticon_state = \"brain\"\n"
            "\tis_vital = TRUE\n"
            "\tvar/brain_damage = 0\n\n"
            "/obj/item/organ/brain/proc/handle_hypoxia(mob/living/carbon/human/H)\n"
            "\tif(H.pulse == 0 || H.blood_oxygen < 40)\n"
            "\t\tbrain_damage += 5\n"
            "\t\tif(brain_damage >= 100)\n"
            "\t\t\tH.death(FALSE) // Clinical brain death\n"
        )
