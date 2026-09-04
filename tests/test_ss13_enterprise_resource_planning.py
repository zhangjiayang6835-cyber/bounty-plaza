"""Unit tests for SS13 Corporate Enterprise Resource Planning (ERP) subsystem.
Resolves Issue #585: [BOUNTY] [PAID BOUNTY] [$40] [paid opire bounty] Add enterprise resource plannin.
"""

import pytest
from scripts.ss13_enterprise_resource_planning import (
    DepartmentCostCenter,
    RequisitionStatus,
    GeneralLedgerEntry,
    InventoryItemRecord,
    PurchaseRequisition,
    EnterpriseResourcePlanningEngine,
)


def test_initial_erp_engine_state():
    erp = EnterpriseResourcePlanningEngine()
    assert erp.station_operating_balance_credits == 50000.0
    assert erp.department_budgets[DepartmentCostCenter.CARGO_LOGISTICS] == 15000.0
    assert len(erp.inventory_catalog) >= 5
    assert len(erp.general_ledger) == 0


def test_double_entry_journal_entry():
    erp = EnterpriseResourcePlanningEngine()
    entry = erp.record_journal_entry(
        cost_center=DepartmentCostCenter.ENGINEERING_POWER,
        debit_account="EXPENSE_ENGINEERING",
        credit_account="STATION_CASH_OPERATING",
        amount=1200.0,
        description="SM Supermatter coolant maintenance recharge"
    )
    assert entry.entry_id == "GL-TX-00001"
    assert entry.amount_credits == 1200.0
    assert len(erp.general_ledger) == 1

    # Negative or zero amount must fail
    with pytest.raises(ValueError, match="Transaction amount must be strictly positive"):
        erp.record_journal_entry(
            cost_center=DepartmentCostCenter.MEDICAL_HEALTH,
            debit_account="EXPENSE_MED",
            credit_account="CASH",
            amount=0.0,
            description="Invalid"
        )


def test_submit_and_fulfill_purchase_requisition():
    erp = EnterpriseResourcePlanningEngine()
    initial_steel = erp.inventory_catalog["MAT-STEEL-01"].quantity_on_hand
    initial_cargo_budget = erp.department_budgets[DepartmentCostCenter.CARGO_LOGISTICS]

    req = erp.submit_purchase_requisition(
        dept=DepartmentCostCenter.CARGO_LOGISTICS,
        item_sku="MAT-STEEL-01",
        quantity=50,
        justification="Structural repairs on exterior hull breach"
    )
    assert req.requisition_id == "PR-0001"
    assert req.estimated_total_cost == 500.0  # 50 * 10.0 credits
    assert req.status == RequisitionStatus.PENDING_APPROVAL

    # Approve and fulfill
    res = erp.approve_and_fulfill_requisition("PR-0001")
    assert res["status"] == "REQUISITION_FULFILLED"
    assert res["cost_incurred"] == 500.0
    assert erp.inventory_catalog["MAT-STEEL-01"].quantity_on_hand == initial_steel + 50
    assert erp.department_budgets[DepartmentCostCenter.CARGO_LOGISTICS] == initial_cargo_budget - 500.0
    assert len(erp.general_ledger) == 1


def test_insufficient_budget_rejection():
    erp = EnterpriseResourcePlanningEngine()
    # Security only has 5,000 budget
    req = erp.submit_purchase_requisition(
        dept=DepartmentCostCenter.SECURITY_JUSTICE,
        item_sku="SEC-STUNBATON-01",
        quantity=100,  # 100 * 75 = 7,500 > 5,000
        justification="Equipping auxiliary volunteer militia"
    )
    res = erp.approve_and_fulfill_requisition(req.requisition_id)
    assert res["status"] == "REQUISITION_REJECTED"
    assert "Insufficient budget" in res["reason"]
    assert req.status == RequisitionStatus.REJECTED


def test_automated_material_requirements_planning():
    erp = EnterpriseResourcePlanningEngine()
    # Artificially drop plasteel stock below reorder point (40)
    erp.inventory_catalog["MAT-PLASTEEL-02"].quantity_on_hand = 20  # optimal is 200

    auto_reqs = erp.run_material_requirements_planning()
    assert len(auto_reqs) == 1
    req = auto_reqs[0]
    assert req.item_sku == "MAT-PLASTEEL-02"
    assert req.quantity == 180  # 200 - 20
    assert "Automated MRP replenishment" in req.justification


def test_kpi_dashboard_metrics():
    erp = EnterpriseResourcePlanningEngine()
    kpi = erp.compute_kpi_dashboard()
    assert kpi["station_operating_cash"] == 50000.0
    assert kpi["total_inventory_valuation"] > 0.0
    assert kpi["total_budget_allocated"] == 50000.0
    assert kpi["pending_requisitions_count"] == 0
    assert kpi["total_ledger_transactions"] == 0


def test_dreammaker_export():
    erp = EnterpriseResourcePlanningEngine()
    dm = erp.export_dreammaker_definitions()
    assert "/obj/machinery/computer/nanotrasen_erp" in dm
    assert "approve_requisition" in dm
