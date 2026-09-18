import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_config_endpoints():
    print("==================================================================")
    print("[*] Testing Google Drive Configuration Endpoints")
    print("==================================================================")

    # 1. GET status
    res = client.get("/api/v1/config/google-drive")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    print(f"  [OK] GET /api/v1/config/google-drive -> is_connected: {data['data']['is_connected']}")

    # 2. Test invalid JSON
    res_bad = client.post("/api/v1/config/google-drive/test", json={"service_account_json": "invalid-json"})
    assert res_bad.status_code == 400
    print("  [OK] POST /api/v1/config/google-drive/test (bad JSON) -> 400 Bad Request")

    print("\n==================================================================")
    print("[SUCCESS] ALL CONFIG ENDPOINTS TESTED!")
    print("==================================================================")


if __name__ == "__main__":
    test_config_endpoints()
