import sys
import os

# Tambahkan root folder ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
from app.schemas.harvest import HarvestCreateRequest
from app.services.normalizer import UnitNormalizer
from app.services.validator import HarvestValidator
from app.services.analytics_service import AnalyticsCalculator
from app.services.harvest_service import harvest_service


def run_verification():
    print("==================================================================")
    print("[*] AgriSensa Harvest Intelligence - Verification & Test Suite")
    print("==================================================================")

    # 1. Normalizer Test
    print("\n[1] Testing Unit Normalizer...")
    assert UnitNormalizer.normalize_area_to_ha(0.5, "ha") == 0.5
    assert UnitNormalizer.normalize_area_to_ha(5000, "m2") == 0.5
    assert UnitNormalizer.normalize_area_to_ha(100, "bata") == 0.14
    assert UnitNormalizer.normalize_weight_to_kg(3.25, "ton") == 3250.0
    assert UnitNormalizer.normalize_weight_to_kg(32.5, "kuintal") == 3250.0
    assert UnitNormalizer.normalize_weight_to_kg(3250, "kg") == 3250.0
    assert UnitNormalizer.normalize_price_per_kg(42000000, "ton") == 42000.0
    print("  [OK] Unit Normalizer (Area, Weight, Price conversion) PASSED")

    # 2. Validator Test
    print("\n[2] Testing Business Logic Validator...")
    valid_payload = HarvestCreateRequest(
        farm_id="FARM-001",
        farmer_id="USR-028",
        commodity="Cabai Merah",
        planting_date=date(2026, 5, 10),
        harvest_date=date(2026, 9, 17),
        land_area=0.5,
        harvest_quantity=3250,
        marketable_quantity=2980,
        damaged_quantity=270,
        selling_price_per_unit=42000,
        production_cost=68500000,
    )
    errors = HarvestValidator.validate_create_payload(valid_payload)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"
    print("  [OK] Valid payload passed validation")

    # Invalid payload: harvest date < planting date
    invalid_date_payload = valid_payload.model_copy(
        update={"planting_date": date(2026, 9, 18), "harvest_date": date(2026, 9, 17)}
    )
    errors = HarvestValidator.validate_create_payload(invalid_date_payload)
    assert any("tidak boleh lebih awal" in err for err in errors)
    print("  [OK] Invalid date sequence correctly caught")

    # Invalid payload: marketable + damaged > harvest quantity
    overflow_payload = valid_payload.model_copy(
        update={"harvest_quantity": 1000, "marketable_quantity": 900, "damaged_quantity": 300}
    )
    errors = HarvestValidator.validate_create_payload(overflow_payload)
    assert any("melebihi total panen" in err for err in errors)
    print("  [OK] Quantity overflow check correctly caught")

    # 3. KPI Analytics Calculator Test (Blueprint Section 7 & 12 Formula Benchmark)
    print("\n[3] Testing Analytics & KPI Calculator...")
    kpis = AnalyticsCalculator.calculate_all_kpis(
        harvest_id="test-h1",
        commodity="Cabai Merah",
        variety="Lado F1",
        harvest_date_str="2026-09-17",
        land_area_ha=0.5,
        harvest_quantity_kg=3250.0,
        marketable_quantity_kg=2980.0,
        damaged_quantity_kg=270.0,
        selling_price_per_kg=42000.0,
        total_production_cost=68500000.0,
    )

    print(f"  - Produktivitas: {kpis.production_kpis.productivity_kg_per_ha} kg/ha (Target: 6500.0)")
    assert kpis.production_kpis.productivity_kg_per_ha == 6500.0
    
    print(f"  - Marketable Yield: {kpis.production_kpis.marketable_yield_percent}% (Target: 91.69%)")
    assert kpis.production_kpis.marketable_yield_percent == 91.69
    
    print(f"  - Loss Rate: {kpis.production_kpis.loss_rate_percent}% (Target: 8.31%)")
    assert kpis.production_kpis.loss_rate_percent == 8.31

    print(f"  - Gross Revenue: Rp {kpis.economic_kpis.gross_revenue_idr:,.2f} (Target: Rp 125,160,000.00)")
    assert kpis.economic_kpis.gross_revenue_idr == 125160000.0

    print(f"  - Net Profit: Rp {kpis.economic_kpis.net_profit_idr:,.2f} (Target: Rp 56,660,000.00)")
    assert kpis.economic_kpis.net_profit_idr == 56660000.0

    print(f"  - Cost per kg: Rp {kpis.economic_kpis.cost_per_kg_idr:,.2f}/kg (Target: Rp 21,076.92/kg)")
    assert kpis.economic_kpis.cost_per_kg_idr == 21076.92

    print(f"  - ROI: {kpis.economic_kpis.roi_percent}% (Target: 82.72%)")
    assert kpis.economic_kpis.roi_percent == 82.72

    print(f"  - BEP (Break-even Price): Rp {kpis.economic_kpis.break_even_price_idr:,.2f}/kg (Target: Rp 22,986.58/kg)")
    assert kpis.economic_kpis.break_even_price_idr == 22986.58
    print("  [OK] All KPI Production & Economic formulas PASSED accurately")

    # 4. Harvest Service & Idempotency Test
    print("\n[4] Testing Harvest Service & Idempotency...")
    # Cek seed data
    records, total = harvest_service.list_harvests()
    assert total >= 1
    print(f"  - Seed harvest count: {total}")

    # Test Ingest Baru dengan Idempotency
    new_req = HarvestCreateRequest(
        idempotency_key="VERIFY-IDEMP-999",
        farm_id="FARM-002",
        farmer_id="USR-028",
        commodity="Jagung Pipil",
        variety="NK212",
        planting_date=date(2026, 4, 1),
        harvest_date=date(2026, 8, 15),
        land_area=1.0,
        land_area_unit="ha",
        harvest_quantity=8.5,
        quantity_unit="ton", # Ton conversion to kg test
        marketable_quantity=8.2,
        damaged_quantity=0.3,
        selling_price_per_unit=5200000, # per ton -> 5200/kg
        production_cost=22000000,
    )
    rec1, is_new1 = harvest_service.create_harvest(new_req)
    assert is_new1 is True
    assert rec1.harvest_quantity_kg == 8500.0 # 8.5 ton -> 8500 kg
    assert rec1.marketable_quantity_kg == 8200.0
    assert rec1.selling_price_per_kg == 5200.0
    print("  [OK] Unit conversion on ingest (8.5 ton -> 8,500 kg) PASSED")

    # Duplicate call with same idempotency key
    rec2, is_new2 = harvest_service.create_harvest(new_req)
    assert is_new2 is False
    assert rec2.harvest_id == rec1.harvest_id
    print("  [OK] Idempotency prevention (duplicate key returns existing record) PASSED")

    print("\n==================================================================")
    print("[SUCCESS] ALL TESTS & FORMULA VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_verification()
