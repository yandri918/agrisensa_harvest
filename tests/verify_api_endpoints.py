import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api():
    print("==================================================================")
    print("[*] Testing FastAPI Endpoints for AgriSensa Harvest Ingest")
    print("==================================================================")

    # 1. Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    print("  [OK] GET /health -> 200 OK")

    # 2. List harvests
    res_list = client.get("/api/v1/harvests")
    assert res_list.status_code == 200
    body = res_list.json()
    assert body["success"] is True
    print(f"  [OK] GET /api/v1/harvests -> 200 OK (total items: {body['data']['total']})")

    # 3. Create harvest (Ingest API)
    payload = {
        "idempotency_key": "HTTP-TEST-IDEMP-001",
        "farm_id": "FARM-001",
        "farmer_id": "USR-028",
        "commodity": "Cabai Merah",
        "variety": "Lado F1",
        "planting_date": "2026-05-10",
        "harvest_date": "2026-09-17",
        "harvest_sequence": 3,
        "land_area": 0.5,
        "land_area_unit": "ha",
        "harvest_quantity": 3250,
        "quantity_unit": "kg",
        "marketable_quantity": 2980,
        "damaged_quantity": 270,
        "selling_price_per_unit": 42000,
        "currency": "IDR",
        "production_cost": 68500000,
        "sales_channel": "pasar_induk",
        "quality_grades": [
            {"grade": "A", "quantity_kg": 1800, "price_per_kg": 45000},
            {"grade": "B", "quantity_kg": 850, "price_per_kg": 39000},
            {"grade": "C", "quantity_kg": 330, "price_per_kg": 30000}
        ]
    }
    res_create = client.post("/api/v1/harvests", json=payload)
    assert res_create.status_code == 201
    created_data = res_create.json()["data"]
    harvest_id = created_data["harvest_id"]
    assert created_data["kpi_summary"]["production_kpis"]["productivity_kg_per_ha"] == 6500.0
    print(f"  [OK] POST /api/v1/harvests -> 201 Created (ID: {harvest_id})")

    # 4. Get detail
    res_detail = client.get(f"/api/v1/harvests/{harvest_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["data"]["harvest_id"] == harvest_id
    print(f"  [OK] GET /api/v1/harvests/{harvest_id} -> 200 OK")

    # 5. Get KPI Endpoint
    res_kpi = client.get(f"/api/v1/analytics/kpis/{harvest_id}")
    assert res_kpi.status_code == 200
    assert res_kpi.json()["data"]["economic_kpis"]["roi_percent"] == 82.72
    print(f"  [OK] GET /api/v1/analytics/kpis/{harvest_id} -> 200 OK (ROI: 82.72%)")

    # 6. Analytics Summary
    res_summary = client.get("/api/v1/analytics/summary")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()["data"]
    assert summary_data["total_records"] >= 1
    print(f"  [OK] GET /api/v1/analytics/summary -> 200 OK (Total Revenue: Rp {summary_data['total_gross_revenue_idr']:,.2f})")

    # 7. Sync Trigger
    res_sync = client.post(f"/api/v1/harvests/{harvest_id}/sync")
    assert res_sync.status_code == 200
    assert res_sync.json()["data"]["status"] == "queued"
    print(f"  [OK] POST /api/v1/harvests/{harvest_id}/sync -> 200 OK (Status: queued)")

    # 8. Soft Delete
    res_del = client.delete(f"/api/v1/harvests/{harvest_id}")
    assert res_del.status_code == 200
    assert res_del.json()["data"]["status"] == "archived"
    print(f"  [OK] DELETE /api/v1/harvests/{harvest_id} -> 200 OK (Status: archived)")

    # 9. Validation Error Check (HTTP 422)
    bad_payload = payload.copy()
    bad_payload["harvest_quantity"] = -100
    res_bad = client.post("/api/v1/harvests", json=bad_payload)
    assert res_bad.status_code == 422
    print("  [OK] POST /api/v1/harvests (Invalid payload) -> 422 Unprocessable Entity")

    print("\n==================================================================")
    print("[SUCCESS] ALL FASTAPI ENDPOINTS VERIFIED & TESTED!")
    print("==================================================================")


if __name__ == "__main__":
    test_api()
