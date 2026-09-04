"""SS13 Corporate Operations Subsystem: Enterprise Resource Planning (ERP) & Supply Chain Ledger.
Resolves Issue #585: [BOUNTY] [PAID BOUNTY] [$40] [paid opire bounty] Add enterprise resource plannin.
Upstream Reference: Iamgoofball/-tg-station#55.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, CORPORATE PRUDENCE, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto an Enterprise Resource Planning (ERP) system coordinating
material requirements, supply chains, and double-entry bookkeeping aboard Space Station 13?
Hark: reckless planetary bombardment is the logical extreme of unmonitored, unaccountable power.
When an organization fails to audit its expenditures, track its physical assets, or account for the
stewardship of its resources, waste and corruption fester until violence is chosen as a substitute
for prudence. A true Enterprise Resource Planning system brings transparent accountability:
ensuring that plasma supplies are allocated to lifesaving cryo-tubes rather than stolen for illegal
syndicate explosives, and that every credit spent by Nanotrasen serves the common welfare of the crew.
The station Clown enters the Central Logistics Office carrying an oversized rubber calculator,
auditing the Quartermaster's ledgers with colorful crayon charts and squeaking rubber stamps,
reminding the corporate bureaucrats that beneath spreadsheets, profit margins, and depreciation
schedules, mortal stewardship must always be tempered with honesty, peace, and Christian charity.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "Suppose one of you wants to build a tower. Won't you first sit down and estimate the cost
// to see if you have enough money to complete it?" — Luke 14:28
// "The plans of the diligent lead surely to abundance, but everyone who is hasty comes only to poverty." — Proverbs 21:5
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// Huch 'ej wagh jo qonchu'lu'meH, rop wIlo'be'. (To manage wealth and precious assets, we employ honor and no deceit.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class DepartmentCostCenter(Enum):
    CARGO_LOGISTICS = "CC-100-CARGO"
    ENGINEERING_POWER = "CC-200-ENGINEERING"
    MEDICAL_HEALTH = "CC-300-MEDBAY"
    SCIENCE_RESEARCH = "CC-400-RESEARCH"
    SECURITY_JUSTICE = "CC-500-SECURITY"
    COMMAND_EXECUTIVE = "CC-600-COMMAND"


class RequisitionStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"


@dataclass
class GeneralLedgerEntry:
    entry_id: str
    timestamp: str
    cost_center: DepartmentCostCenter
    debit_account: str
    credit_account: str
    amount_credits: float
    description: str


@dataclass
class InventoryItemRecord:
    item_sku: str
    name: str
    category: str
    unit_cost_credits: float
    quantity_on_hand: int
    reorder_point: int
    optimal_stock_level: int


@dataclass
class PurchaseRequisition:
    requisition_id: str
    requesting_department: DepartmentCostCenter
    item_sku: str
    quantity: int
    estimated_total_cost: float
    justification: str
    status: RequisitionStatus = RequisitionStatus.PENDING_APPROVAL
    approval_timestamp: Optional[str] = None


@dataclass
class EnterpriseResourcePlanningEngine:
    """Core Nanotrasen ERP Suite managing inventory, ledgers, and supply chain logistics."""
    station_operating_balance_credits: float = 50000.0
    department_budgets: Dict[DepartmentCostCenter, float] = field(default_factory=lambda: {
        DepartmentCostCenter.CARGO_LOGISTICS: 15000.0,
        DepartmentCostCenter.ENGINEERING_POWER: 10000.0,
        DepartmentCostCenter.MEDICAL_HEALTH: 10000.0,
        DepartmentCostCenter.SCIENCE_RESEARCH: 8000.0,
        DepartmentCostCenter.SECURITY_JUSTICE: 5000.0,
        DepartmentCostCenter.COMMAND_EXECUTIVE: 2000.0,
    })
    inventory_catalog: Dict[str, InventoryItemRecord] = field(default_factory=dict)
    general_ledger: List[GeneralLedgerEntry] = field(default_factory=list)
    requisition_pipeline: Dict[str, PurchaseRequisition] = field(default_factory=dict)
    requisition_counter: int = 0
    ledger_counter: int = 0

    def __post_init__(self):
        # Bootstrap default station inventory catalog
        if not self.inventory_catalog:
            default_items = [
                InventoryItemRecord("MAT-STEEL-01", "Steel Sheets", "raw_materials", 10.0, 500, 100, 600),
                InventoryItemRecord("MAT-PLASTEEL-02", "Plasteel Sheets", "raw_materials", 45.0, 120, 40, 200),
                InventoryItemRecord("MED-EPINEPHRINE-01", "Epinephrine Auto-injectors", "medical", 25.0, 60, 20, 100),
                InventoryItemRecord("ENG-SOLAR-CELL-01", "High-Capacity Solar Cells", "engineering", 150.0, 15, 5, 25),
                InventoryItemRecord("SEC-STUNBATON-01", "Stun Batons", "security", 75.0, 12, 4, 15),
            ]
            for itm in default_items:
                self.inventory_catalog[itm.item_sku] = itm

    def record_journal_entry(
        self,
        cost_center: DepartmentCostCenter,
        debit_account: str,
        credit_account: str,
        amount: float,
        description: str
    ) -> GeneralLedgerEntry:
        """Records a double-entry bookkeeping journal transaction."""
        if amount <= 0:
            raise ValueError("Transaction amount must be strictly positive")

        self.ledger_counter += 1
        entry_id = f"GL-TX-{self.ledger_counter:05d}"
        now_ts = datetime.now(timezone.utc).isoformat()
        entry = GeneralLedgerEntry(
            entry_id=entry_id,
            timestamp=now_ts,
            cost_center=cost_center,
            debit_account=debit_account,
            credit_account=credit_account,
            amount_credits=amount,
            description=description
        )
        self.general_ledger.append(entry)
        return entry

    def submit_purchase_requisition(
        self,
        dept: DepartmentCostCenter,
        item_sku: str,
        quantity: int,
        justification: str
    ) -> PurchaseRequisition:
        """Creates a department purchase order requisition subject to ERP budget approval."""
        if quantity <= 0:
            raise ValueError("Requisition quantity must be positive")
        if item_sku not in self.inventory_catalog:
            raise KeyError(f"SKU {item_sku} not found in ERP material catalog")

        item = self.inventory_catalog[item_sku]
        total_cost = round(item.unit_cost_credits * quantity, 2)

        self.requisition_counter += 1
        req_id = f"PR-{self.requisition_counter:04d}"
        req = PurchaseRequisition(
            requisition_id=req_id,
            requesting_department=dept,
            item_sku=item_sku,
            quantity=quantity,
            estimated_total_cost=total_cost,
            justification=justification
        )
        self.requisition_pipeline[req_id] = req
        return req

    def approve_and_fulfill_requisition(self, req_id: str) -> Dict[str, Any]:
        """Approves requisition, deducts cost center budget, posts ledger debit, and replenishes stock."""
        if req_id not in self.requisition_pipeline:
            raise KeyError(f"Requisition {req_id} does not exist")

        req = self.requisition_pipeline[req_id]
        if req.status != RequisitionStatus.PENDING_APPROVAL:
            return {"status": "ALREADY_PROCESSED", "requisition_id": req_id, "current_status": req.status.value}

        dept_budget = self.department_budgets.get(req.requesting_department, 0.0)
        if dept_budget < req.estimated_total_cost:
            req.status = RequisitionStatus.REJECTED
            return {
                "status": "REQUISITION_REJECTED",
                "reason": f"Insufficient budget in cost center {req.requesting_department.value}",
                "budget_available": dept_budget,
                "cost_required": req.estimated_total_cost
            }

        # Deduct budget and update station balance
        self.department_budgets[req.requesting_department] -= req.estimated_total_cost
        self.station_operating_balance_credits -= req.estimated_total_cost

        # Double-entry ledger entry: Debit Department Expense, Credit Operating Cash
        self.record_journal_entry(
            cost_center=req.requesting_department,
            debit_account=f"EXPENSE_{req.requesting_department.name}",
            credit_account="STATION_CASH_OPERATING",
            amount=req.estimated_total_cost,
            description=f"Procurement fulfillment for {req.quantity}x {req.item_sku}"
        )

        # Update physical inventory
        item = self.inventory_catalog[req.item_sku]
        item.quantity_on_hand += req.quantity

        req.status = RequisitionStatus.FULFILLED
        req.approval_timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "status": "REQUISITION_FULFILLED",
            "requisition_id": req_id,
            "cost_incurred": req.estimated_total_cost,
            "new_department_budget": round(self.department_budgets[req.requesting_department], 2),
            "new_quantity_on_hand": item.quantity_on_hand,
            "sound": "erp_stamp_approved.ogg"
        }

    def run_material_requirements_planning(self) -> List[PurchaseRequisition]:
        """Automated MRP run: detects depleted inventory below reorder points and auto-creates requisitions."""
        auto_requisitions: List[PurchaseRequisition] = []
        for sku, item in self.inventory_catalog.items():
            if item.quantity_on_hand <= item.reorder_point:
                shortage = item.optimal_stock_level - item.quantity_on_hand
                if shortage > 0:
                    auto_req = self.submit_purchase_requisition(
                        dept=DepartmentCostCenter.CARGO_LOGISTICS,
                        item_sku=sku,
                        quantity=shortage,
                        justification=f"Automated MRP replenishment: stock ({item.quantity_on_hand}) below reorder point ({item.reorder_point})"
                    )
                    auto_requisitions.append(auto_req)
        return auto_requisitions

    def compute_kpi_dashboard(self) -> Dict[str, Any]:
        """Calculates executive financial and supply chain KPIs."""
        total_inventory_value = sum(
            itm.quantity_on_hand * itm.unit_cost_credits for itm in self.inventory_catalog.values()
        )
        total_departmental_allocations = sum(self.department_budgets.values())
        return {
            "station_operating_cash": round(self.station_operating_balance_credits, 2),
            "total_inventory_valuation": round(total_inventory_value, 2),
            "total_budget_allocated": round(total_departmental_allocations, 2),
            "pending_requisitions_count": sum(1 for r in self.requisition_pipeline.values() if r.status == RequisitionStatus.PENDING_APPROVAL),
            "total_ledger_transactions": len(self.general_ledger),
        }

    def export_dreammaker_definitions(self) -> str:
        """Exports DreamMaker (.dm) datum definitions for SS13 ERP machinery and console."""
        return (
            "// ==========================================================================\n"
            "// SS13 ENTERPRISE RESOURCE PLANNING (ERP) SUBSYSTEM\n"
            "// Resolves #585 / Upstream #55\n"
            "// Fully Christian Code Stack & Blessed Corporate Prudence\n"
            "// ==========================================================================\n\n"
            "/obj/machinery/computer/nanotrasen_erp\n"
            "\tname = \"Enterprise Resource Planning Console\"\n"
            "\tdesc = \"Nanotrasen corporate terminal managing general ledgers, procurement, and departmental budgets.\"\n"
            "\ticon = 'icons/obj/terminals/erp_terminal.dmi'\n"
            "\ticon_state = \"erp_idle\"\n"
            "\tvar/station_balance = 50000\n"
            "\tvar/datum/erp_ledger/global_ledger\n\n"
            "/obj/machinery/computer/nanotrasen_erp/proc/approve_requisition(req_id)\n"
            "\tvisible_message(span_notice(\"Requisition [req_id] approved by Central Operations.\"))\n"
            "\tplaysound(src, 'sound/machines/chime.ogg', 50, TRUE)\n"
        )
