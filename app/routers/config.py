import json
import logging
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
from app.schemas.common import ApiResponse
from app.config import settings
from app.services.google_drive_service import google_drive_service

router = APIRouter(prefix="/config", tags=["Configuration"])
logger = logging.getLogger("agrisensa.config")


class GoogleDriveConfigRequest(BaseModel):
    service_account_json: str = Field(..., description="Isi teks raw JSON dari Service Account Key")
    folder_id: Optional[str] = Field(None, description="ID folder root Google Drive")
    folder_name: Optional[str] = Field("AgriSensa_Harvest_Reports", description="Nama folder default")


class GoogleDriveStatusResponse(BaseModel):
    is_connected: bool
    client_email: Optional[str] = None
    project_id: Optional[str] = None
    folder_id: Optional[str] = None
    folder_name: str
    message: str


@router.get("/google-drive", response_model=ApiResponse[GoogleDriveStatusResponse])
def get_google_drive_status():
    """Mengambil status koneksi Google Drive saat ini."""
    is_conn = google_drive_service.is_authenticated
    client_email = None
    project_id = None

    if is_conn and google_drive_service._service:
        try:
            # Dapatkan informasi client email jika tersedia
            if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                parsed = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                client_email = parsed.get("client_email")
                project_id = parsed.get("project_id")
        except Exception:
            pass

    msg = "Google Drive terhubung dan siap digunakan." if is_conn else "Google Drive belum terhubung. Silakan masukkan kredensial Service Account."

    return ApiResponse(
        success=True,
        message="Status Google Drive berhasil diambil.",
        data=GoogleDriveStatusResponse(
            is_connected=is_conn,
            client_email=client_email,
            project_id=project_id,
            folder_id=settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
            folder_name=settings.GOOGLE_DRIVE_FOLDER_NAME,
            message=msg
        )
    )


@router.post("/google-drive/test", response_model=ApiResponse[dict])
def test_google_drive_connection(payload: GoogleDriveConfigRequest):
    """Menguji kredensial Service Account secara langsung ke Google Drive API."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        info = json.loads(payload.service_account_json)
        client_email = info.get("client_email")
        project_id = info.get("project_id")

        if not client_email:
            raise ValueError("Berkas JSON tidak memiliki field 'client_email' yang valid.")

        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.metadata.readonly"]
        )
        service = build("drive", "v3", credentials=creds)

        # Lakukan panggilan uji coba ke Google Drive
        about = service.about().get(fields="user").execute()
        user_name = about.get("user", {}).get("displayName", "Service Account")

        return ApiResponse(
            success=True,
            message=f"Koneksi berhasil! Service Account: {client_email}",
            data={
                "client_email": client_email,
                "project_id": project_id,
                "user_name": user_name,
                "verified": True
            }
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format JSON tidak valid. Pastikan Anda menyalin seluruh isi file .json kredensial."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal menghubungkan ke Google Drive: {str(e)}"
        )


@router.post("/google-drive", response_model=ApiResponse[dict])
def save_google_drive_config(payload: GoogleDriveConfigRequest):
    """Menyimpan dan menerapkan konfigurasi Google Drive pada runtime aplikasi."""
    try:
        # 1. Validasi JSON
        info = json.loads(payload.service_account_json)
        client_email = info.get("client_email")
        
        # 2. Update settings runtime
        settings.GOOGLE_SERVICE_ACCOUNT_JSON = payload.service_account_json.strip()
        if payload.folder_id:
            settings.GOOGLE_DRIVE_ROOT_FOLDER_ID = payload.folder_id.strip()
        if payload.folder_name:
            settings.GOOGLE_DRIVE_FOLDER_NAME = payload.folder_name.strip()

        # 3. Re-inisialisasi service
        google_drive_service._init_client()

        if not google_drive_service.is_authenticated:
            raise ValueError("Kredensial tersimpan namun inisialisasi client gagal.")

        return ApiResponse(
            success=True,
            message=f"Konfigurasi Google Drive berhasil disimpan dan diaktifkan untuk {client_email}.",
            data={
                "is_connected": True,
                "client_email": client_email,
                "folder_id": settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal menerapkan konfigurasi Google Drive: {str(e)}"
        )


@router.post("/google-drive/test-upload", response_model=ApiResponse[dict])
def test_upload_to_drive():
    """Menguji coba upload berkas pengujian langsung ke Google Drive."""
    if not google_drive_service.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive belum terkonfigurasi. Silakan simpan kredensial Service Account terlebih dahulu."
        )

    try:
        import io
        from googleapiclient.http import MediaIoBaseUpload

        service = google_drive_service._service
        root_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip() if settings.GOOGLE_DRIVE_ROOT_FOLDER_ID else None
        if not root_id:
            root_id = google_drive_service.get_or_create_folder(settings.GOOGLE_DRIVE_FOLDER_NAME)

        test_content = f"Uji Coba Koneksi AgriSensa Harvest Intelligence ke Google Drive.\nWaktu: {datetime.utcnow().isoformat()}\nService Account: {google_drive_service.client_email}\n".encode("utf-8")

        file_metadata = {
            "name": "AgriSensa_Connection_Test.txt",
            "mimeType": "text/plain"
        }
        if root_id:
            file_metadata["parents"] = [root_id]

        media = MediaIoBaseUpload(io.BytesIO(test_content), mimetype="text/plain", resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink", supportsAllDrives=True).execute()

        # Set read permission
        try:
            service.permissions().create(fileId=file.get("id"), body={"type": "anyone", "role": "reader"}, supportsAllDrives=True).execute()
        except Exception:
            pass

        return ApiResponse(
            success=True,
            message=f"File uji coba 'AgriSensa_Connection_Test.txt' berhasil diunggah ke Google Drive!",
            data={
                "file_id": file.get("id"),
                "file_name": file.get("name"),
                "web_view_link": file.get("webViewLink")
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal mengunggah file uji coba ke Google Drive: {str(e)}"
        )

