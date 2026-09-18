import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.harvest_service import harvest_service
from app.services.google_drive_service import google_drive_service


def test_google_drive_integration():
    print("==================================================================")
    print("[*] Testing Google Drive Service & Upload Flow")
    print("==================================================================")

    # 1. Check client state
    print(f"  - Is Authenticated: {google_drive_service.is_authenticated}")

    # 2. Get sample record
    records, total = harvest_service.list_harvests()
    assert total >= 1
    sample_record = records[0]

    # 3. Trigger upload
    res = google_drive_service.upload_harvest_report(sample_record)
    print(f"  - Upload Response: {res}")

    assert res["success"] is True
    assert "file_id" in res
    assert "folder_path" in res
    print("  [OK] Google Drive report packaging & upload logic PASSED")

    print("\n==================================================================")
    print("[SUCCESS] GOOGLE DRIVE SERVICE INTEGRATION VERIFIED!")
    print("==================================================================")


if __name__ == "__main__":
    test_google_drive_integration()
