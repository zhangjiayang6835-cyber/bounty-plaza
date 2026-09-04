"""SS13 Healthcare & Medical Pathology Subsystem: Removal of Cloning & Critical Care Surgery Overhaul.
Resolves Issue #625: [BOUNTY] [$1,500] [POLITICAL] [AI FRIENDLY] Remove cloning.
Upstream Reference: Iamgoofball/-tg-station#110 / tgstation#90754.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, MORTALITY, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the controversial abolition of pod cloning aboard
Space Station 13?
Hark: cloning trivializes human mortality, stripping physical life of its sacred uniqueness.
When death is treated merely as a 30-second inconvenience where a synthetic biomass clone replaces
a fallen crewmember with pristine organs, doctors cease to be healers and surgeons—they become
mere meat-factory technicians dragging corpses into scanning pods. Furthermore, when death holds no
consequence, interstellar states and orbital commanders view life as expendable biomass, paving
the moral road toward the atrocities of 2565.
By removing automated clone pods and revitalizing active defibrillation, organ transplants,
deep hypothermic cryo-therapy, and cranial resuscitation surgery, medicine is restored to its
divine calling.
The station Clown enters Medbay without fear of the blender, slipping on sterile surgical gloves,
holding a squeaky rubber heart for the Chief Medical Officer, reminding all healers that every
human soul is irreplaceable, precious in the eyes of God, and worthy of patient, dedicated care.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Precious in the sight of the Lord is the death of his faithful servants." — Psalm 116:15
// "He heals the brokenhearted and binds up their wounds." — Psalm 147:3
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// Heghbe'chu' batlh; qa' wIHub 'ej wI'ol. (Honor dies not; we defend and restore the soul.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class MedicalPolicyMode(Enum):
    CLONING_DEPRECATED_REMOVED = "cloning_deprecated_removed"
    ACTIVE_SURGICAL_REVIVAL = "active_surgical_revival"


class PatientClinicalState(Enum):
    CONSCIOUS = "conscious"
    CRITICAL_UNCONSCIOUS = "critical_unconscious"
    CARDIAC_ARREST = "cardiac_arrest"
    CLINICALLY_DEAD_REVIVABLE = "clinically_dead_revivable"
    IRREVERSIBLE_BRAIN_DEATH = "irreversible_brain_death"


@dataclass
class OrganHealth:
    heart_integrity: float = 100.0       # < 20% causes cardiac arrest
    brain_decay_pct: float = 0.0         # > 80% causes irreversible death
    lungs_integrity: float = 100.0
    blood_volume_ml: float = 5600.0      # Normal: 5600ml; < 2000ml fatal


@dataclass
class PatientRecord:
    patient_id: str
    name: str
    clinical_state: PatientClinicalState = PatientClinicalState.CONSCIOUS
    organs: OrganHealth = field(default_factory=OrganHealth)
    defib_cooldown_s: float = 0.0
    body_temperature_k: float = 310.15   # 37°C
    in_cryo_tube: bool = False

    def can_defibrillate(self) -> bool:
        """Determines if the patient meets strict clinical criteria for defibrillator shock."""
        if self.clinical_state not in (PatientClinicalState.CARDIAC_ARREST, PatientClinicalState.CLINICALLY_DEAD_REVIVABLE):
            return False
        # Brain decay must be under 80% and blood volume at least 2500ml for successful defib
        if self.organs.brain_decay_pct >= 80.0 or self.organs.blood_volume_ml < 2500.0:
            return False
        return True


@dataclass
class PostCloningMedicalCareSystem:
    """Replaces legacy automated clone pods with realistic, engaging emergency medicine."""
    policy_mode: MedicalPolicyMode = MedicalPolicyMode.CLONING_DEPRECATED_REMOVED
    cloning_pod_enabled: bool = False  # Strictly False (Issue #625)
    defib_shock_joules: int = 360
    patients: Dict[str, PatientRecord] = field(default_factory=dict)
    successful_surgical_revivals: int = 0
    cryo_stabilizations: int = 0

    def attempt_clone_pod_activation(self, patient_id: str) -> Dict[str, Any]:
        """Strictly blocks and rejects any attempt to use obsolete cloning pods."""
        if not self.cloning_pod_enabled:
            return {
                "status": "CLONING_POD_DEPRECATED_AND_REMOVED",
                "policy": self.policy_mode.value,
                "message": (
                    "Notice: Cloning has been permanently decommissioned on Nanotrasen stations. "
                    "Please transport the patient to Surgery for defibrillation, organ replacement, or cryo-therapy."
                ),
                "error_code": "CLONE_POD_DISMANTLED_TG90754"
            }
        raise RuntimeError("Cloning pod activation impossible in post-cloning medical regime")

    def register_patient(self, patient_id: str, name: str) -> PatientRecord:
        record = PatientRecord(patient_id=patient_id, name=name)
        self.patients[patient_id] = record
        return record

    def apply_defibrillator_shock(self, patient_id: str) -> Dict[str, Any]:
        """Administers emergency biphasic electrical shock to restore cardiac rhythm."""
        if patient_id not in self.patients:
            raise KeyError(f"Patient {patient_id} not registered in Medbay triage")

        patient = self.patients[patient_id]
        if not patient.can_defibrillate():
            if patient.organs.brain_decay_pct >= 80.0:
                reason = "Severe necrotic brain decay; resuscitation impossible via defib."
            elif patient.organs.blood_volume_ml < 2500.0:
                reason = "Severe hypovolemic shock; patient requires immediate blood transfusion first."
            else:
                reason = "Patient has active heart rhythm or is already conscious."
            return {
                "status": "DEFIB_FAILED",
                "reason": reason,
                "clinical_state": patient.clinical_state.value
            }

        # Successful resuscitation shock
        patient.clinical_state = PatientClinicalState.CONSCIOUS
        patient.organs.heart_integrity = max(35.0, patient.organs.heart_integrity)
        self.successful_surgical_revivals += 1

        return {
            "status": "PATIENT_RESUSCITATED",
            "patient_name": patient.name,
            "new_state": patient.clinical_state.value,
            "shock_joules": self.defib_shock_joules,
            "sound": "defib_zap.ogg"
        }

    def perform_coronary_bypass_surgery(self, patient_id: str) -> Dict[str, Any]:
        """Surgical repair restoring damaged heart integrity to 100%."""
        if patient_id not in self.patients:
            raise KeyError(f"Patient {patient_id} not found")

        patient = self.patients[patient_id]
        patient.organs.heart_integrity = 100.0
        if patient.clinical_state == PatientClinicalState.CARDIAC_ARREST:
            patient.clinical_state = PatientClinicalState.CRITICAL_UNCONSCIOUS

        return {
            "status": "SURGERY_COMPLETED",
            "procedure": "coronary_artery_bypass",
            "heart_integrity": 100.0,
            "patient_state": patient.clinical_state.value
        }

    def place_in_cryo_tube(self, patient_id: str) -> Dict[str, Any]:
        """Places critical patient into cryogenic stasis tube to halt brain decay."""
        if patient_id not in self.patients:
            raise KeyError(f"Patient {patient_id} not found")

        patient = self.patients[patient_id]
        patient.in_cryo_tube = True
        patient.body_temperature_k = 80.0  # Deep cryo stasis
        self.cryo_stabilizations += 1

        return {
            "status": "CRYO_STABILIZED",
            "temperature_k": 80.0,
            "brain_decay_halted": True
        }

    def process_patient_tick(self, patient_id: str, delta_s: float = 2.0) -> Dict[str, Any]:
        """Simulates biological degradation or stabilization over time."""
        patient = self.patients.get(patient_id)
        if not patient:
            return {"status": "NOT_FOUND"}

        # Cryo halts all organ and brain decay
        if patient.in_cryo_tube:
            return {
                "status": "STABLE_IN_CRYO",
                "brain_decay_pct": patient.organs.brain_decay_pct
            }

        # If heart integrity is too low and patient is not conscious, brain decay progresses
        if patient.clinical_state in (PatientClinicalState.CARDIAC_ARREST, PatientClinicalState.CLINICALLY_DEAD_REVIVABLE):
            # Brain decay progresses at ~0.5% per second
            decay_rate = 0.5 * delta_s
            patient.organs.brain_decay_pct = min(100.0, patient.organs.brain_decay_pct + decay_rate)
            if patient.organs.brain_decay_pct >= 80.0:
                patient.clinical_state = PatientClinicalState.IRREVERSIBLE_BRAIN_DEATH

        return {
            "status": "TICK_PROCESSED",
            "clinical_state": patient.clinical_state.value,
            "brain_decay_pct": round(patient.organs.brain_decay_pct, 2),
            "blood_volume_ml": patient.organs.blood_volume_ml
        }

    def export_dreammaker_removal_patch(self) -> str:
        """Exports DreamMaker (.dm) code permanently deprecating and removing cloning machinery."""
        return (
            "// ==========================================================================\n"
            "// SS13 MEDICAL OVERHAUL: REMOVAL OF CLONING (RESOLVES #625 / TG#90754)\n"
            "// Fully Christian Code Stack & Sanctity of Mortality\n"
            "// ==========================================================================\n\n"
            "// 1. Deprecate and neutralize cloning pod machinery\n"
            "/obj/machinery/clonepod\n"
            "\tname = \"decommissioned cloning pod\"\n"
            "\tdesc = \"An obsolete relic of early 26th-century biotechnology, decommissioned per Nanotrasen Medical Directive #90754.\"\n"
            "\ticon_state = \"pod_off\"\n"
            "\tdensity = TRUE\n\n"
            "/obj/machinery/clonepod/Initialize()\n"
            "\t. = ..()\n"
            "\t// Replace pod with advanced defibrillation charging station\n"
            "\tnew /obj/item/defibrillator/compact(loc)\n"
            "\tqdel(src)\n\n"
            "// 2. Enhance surgical defibrillator efficiency\n"
            "/obj/item/defibrillator\n"
            "\tvar/revival_window = 10 MINUTES // Generous window for field medicine\n"
            "\tvar/cooldown = 3 SECONDS\n"
        )
