import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.harvest import HarvestCreateRequest
from app.services.normalizer import UnitNormalizer
from app.services.validator import HarvestValidator
from app.services.analytics_service import AnalyticsCalculator

client = TestClient(app)


# 1. UNIT NORMALIZER TESTS
def test_unit_normalizer():
    # Luas
    assert UnitNormalizer.normalize_area_to_ha(0.5, "ha") == 0.5
    assert UnitNormalizer.normalize_area_to_ha(5000, "m2") == 0.5
    assert UnitNormalizer.normalize_area_to_ha(100, "bata") == 0.14
    
    # Berat
    assert UnitNormalizer.normalize_weight_to_kg(3.25, "ton") == 3250.0
    assert UnitNormalizer.normalize_weight_to_kg(32.5, "kuintal") == 3250.0
    assert UnitNormalizer.normalize_weight_to_kg(3250, "kg") == 3250.0
    
    # Harga
    assert UnitNormalizer.normalize_price_per_kg(42000000, "ton") == 42000.0


# 2. VALIDATOR TESTS
def test_harvest_validator():
    # Valid Payload
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
    assert len(errors) == 0

    # Invalid: Harvest date earlier than planting date
    invalid_date_payload = valid_payload.model_copy(
        update={"planting_date": date(2026, 9, 18), "harvest_date": date(2026, 9, 17)}
    )
    errors = HarvestValidator.validate_create_payload(invalid_date_payload)
    assert any("tidak boleh lebih awal" in err for err in errors)

    # Invalid: Total marketable + damaged exceeds harvest quantity
    overflow_payload = valid_payload.model_copy(
        update={"harvest_quantity": 1000, "marketable_quantity": 900, "damaged_quantity": 300}
    )
    errors = HarvestValidator.validate_create_payload(overflow_payload)
    assert any("melebihi total panen" in err for err in errors)


# 3. KPI ANALYTICS FORMULA TESTS
def test_analytics_calculator():
    # Sesuai data Section 7 blueprint:
    # Luas = 0.5 ha, Panen = 3250 kg, Layak = 2980 kg, Rusak = 270 kg, Harga = Rp 42.000, Biaya = Rp 68.500.000
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

    # Produktivitas: 3250 / 0.5 = 6500 kg/ha
    assert kpis.production_kpis.productivity_kg_per_ha == 6500.0
    
    # Marketable Yield: (2980 / 3250) * 100 = 91.69%
    assert kpis.production_kpis.marketable_yield_percent == 91.69
    
    # Loss Rate: (270 / 3250) * 100 = 8.31%
    assert kpis.production_kpis.loss_rate_percent == 8.31

    # Gross Revenue: 2980 * 42000 = 125,160,000 IDR
    assert kpis.economic_kpis.gross_revenue_idr == 125160000.0
    
    # Net Profit: 125,160,000 - 68,500,000 = 56,660,000 IDR
    assert kpis.economic_kpis.net_profit_idr == 56660000.0
    
    # Cost per kg: 68,500,000 / 3250 = 21076.92 IDR/kg
    assert kpis.economic_kpis.cost_per_kg_idr == 21076.92
    
    # ROI: (56,660,000 / 68,500,000) * 100 = 82.72%
    assert kpis.economic_kpis.roi_percent == 82.72
    
    # Break-even Price: 68,500,000 / 2980 = 22986.58 IDR/kg
    assert kpis.economic_kpis.break_even_price_idr == 22986.58


# 4. FASTAPI ENDPOINTS TESTS
def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_harvest_endpoint_and_idempotency():
    payload = {
        "idempotency_key": "TEST-IDEMP-001",
        "farm_id": "FARM-TEST",
        "farmer_id": "FARMER-TEST",
        "commodity": "Tomat Buah",
        "variety": "Servo F1",
        "planting_date": "2026-06-01",
        "harvest_date": "2026-08-20",
        "harvest_sequence": 1,
        "land_area": 0.25,
        "land_area_unit": "ha",
        "harvest_quantity": 2500,
        "quantity_unit": "kg",
        "marketable_quantity": 2300,
        "damaged_quantity": 200,
        "selling_price_per_unit": 12000,
        "production_cost": 15000000,
        "sales_channel": "supermarket",
        "quality_grades": [
            {"grade": "A", "quantity_kg": 1500, "price_per_kg": 14000},
            {"grade": "B", "quantity_kg": 800, "price_per_kg": 10000}
        ]
    }

    # Unauthenticated call should be rejected with 401
    res_unauth = client.post("/api/v1/harvests", json=payload)
    assert res_unauth.status_code == 401

    auth_headers = {"X-User-Id": "user_test_runner_1", "X-User-Email": "tester@agrisensa.ai"}

    # 1st Call: Create with auth
    res1 = client.post("/api/v1/harvests", json=payload, headers=auth_headers)
    assert res1.status_code == 201
    body1 = res1.json()
    assert body1["success"] is True
    harvest_id = body1["data"]["harvest_id"]
    assert body1["data"]["kpi_summary"]["production_kpis"]["productivity_kg_per_ha"] == 10000.0

    # 2nd Call: Same Idempotency Key -> Should return same harvest_id
    res2 = client.post("/api/v1/harvests", json=payload, headers=auth_headers)
    assert res2.status_code == 201
    body2 = res2.json()
    assert body2["data"]["harvest_id"] == harvest_id


def test_get_harvest_and_analytics_summary():
    auth_headers = {"X-User-Id": "user_test_runner_1", "X-User-Email": "tester@agrisensa.ai"}

    # Query list
    res = client.get("/api/v1/harvests", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert len(items) >= 1

    # Get single detail
    harvest_id = items[0]["harvest_id"]
    res_detail = client.get(f"/api/v1/harvests/{harvest_id}", headers=auth_headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["harvest_id"] == harvest_id

    # Get analytics summary
    res_summary = client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert res_summary.status_code == 200
    summary = res_summary.json()["data"]
    assert summary["total_records"] >= 1
    assert summary["total_harvest_kg"] > 0


def test_validation_error_response():
    auth_headers = {"X-User-Id": "user_test_runner_1", "X-User-Email": "tester@agrisensa.ai"}

    # Invalid request: negative harvest quantity
    bad_payload = {
        "farm_id": "FARM-BAD",
        "farmer_id": "FARMER-BAD",
        "commodity": "Jagung",
        "planting_date": "2026-05-01",
        "harvest_date": "2026-08-01",
        "land_area": 1.0,
        "land_area_unit": "ha",
        "harvest_quantity": -500, # Invalid
        "quantity_unit": "kg"
    }
    res = client.post("/api/v1/harvests", json=bad_payload, headers=auth_headers)
    assert res.status_code == 422
