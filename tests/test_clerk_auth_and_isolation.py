import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.db import db_manager

client = TestClient(app)


def test_auth_me_unauthenticated_rejected():
    """Menguji bahwa /auth/me tanpa autentikasi Clerk ditolak dengan 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Autentikasi diperlukan" in response.json()["detail"]


def test_auth_me_authenticated():
    """Menguji /auth/me saat menyertakan token/header otentikasi."""
    headers = {"X-User-Id": "user_clerk_verified_123", "X-User-Email": "petani@agrisensa.ai"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "user_clerk_verified_123"
    assert "stats" in data["data"]


def test_auth_sync_and_provisioning():
    """Menguji /auth/sync dan registrasi otomatis akun Clerk baru di database."""
    user_id = "user_test_clerk_888"
    headers = {
        "X-User-Id": user_id,
        "X-User-Email": "budi.santoso@agrisensa.ai",
        "X-User-Name": "Budi Santoso",
    }
    response = client.post("/api/v1/auth/sync", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == user_id
    assert data["data"]["email"] == "budi.santoso@agrisensa.ai"
    assert data["data"]["full_name"] == "Budi Santoso"


def test_user_data_isolation():
    """Menguji bahwa User A dan User B memiliki database dan rekapitulasi panen yang terisolasi."""
    user_a = "user_clerk_petani_A"
    user_b = "user_clerk_petani_B"

    # User A membuat panen Cabai
    payload_a = {
        "farm_id": "FARM-A",
        "farmer_id": user_a,
        "commodity": "Cabai Rawit Merah",
        "variety": "Ori 212",
        "planting_date": "2026-06-01",
        "harvest_date": "2026-09-01",
        "harvest_sequence": 1,
        "land_area": 0.25,
        "land_area_unit": "ha",
        "harvest_quantity": 1200,
        "quantity_unit": "kg",
        "marketable_quantity": 1150,
        "damaged_quantity": 50,
        "selling_price_per_unit": 50000,
        "production_cost": 25000000,
        "notes": "Panen milik User A"
    }
    resp_a = client.post("/api/v1/harvests", json=payload_a, headers={"X-User-Id": user_a})
    assert resp_a.status_code == 201
    harvest_a_id = resp_a.json()["data"]["harvest_id"]

    # User B membuat panen Jagung Manis
    payload_b = {
        "farm_id": "FARM-B",
        "farmer_id": user_b,
        "commodity": "Jagung Manis",
        "variety": "Talenta",
        "planting_date": "2026-06-15",
        "harvest_date": "2026-08-30",
        "harvest_sequence": 1,
        "land_area": 0.5,
        "land_area_unit": "ha",
        "harvest_quantity": 4000,
        "quantity_unit": "kg",
        "marketable_quantity": 3800,
        "damaged_quantity": 200,
        "selling_price_per_unit": 8000,
        "production_cost": 12000000,
        "notes": "Panen milik User B"
    }
    resp_b = client.post("/api/v1/harvests", json=payload_b, headers={"X-User-Id": user_b})
    assert resp_b.status_code == 201
    harvest_b_id = resp_b.json()["data"]["harvest_id"]

    # User A mengambil daftar panen: hanya boleh melihat panen User A (Cabai Rawit Merah)
    list_a = client.get("/api/v1/harvests", headers={"X-User-Id": user_a}).json()
    commodities_a = [item["commodity"] for item in list_a["data"]["items"]]
    assert "Cabai Rawit Merah" in commodities_a
    assert "Jagung Manis" not in commodities_a

    # User B mengambil daftar panen: hanya boleh melihat panen User B (Jagung Manis)
    list_b = client.get("/api/v1/harvests", headers={"X-User-Id": user_b}).json()
    commodities_b = [item["commodity"] for item in list_b["data"]["items"]]
    assert "Jagung Manis" in commodities_b
    assert "Cabai Rawit Merah" not in commodities_b

    # User B tidak boleh dapat mengakses detail panen milik User A
    detail_unauth = client.get(f"/api/v1/harvests/{harvest_a_id}", headers={"X-User-Id": user_b})
    assert detail_unauth.status_code == 404
