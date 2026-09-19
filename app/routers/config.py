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
    webhook_url: Optional[str] = Field(None, description="URL Web App Google Apps Script (Metode Simpel & Direkomendasikan)")
    service_account_json: Optional[str] = Field(None, description="Isi teks raw JSON dari Service Account Key (Opsional)")
    folder_id: Optional[str] = Field(None, description="ID folder root Google Drive (Opsional)")
    folder_name: Optional[str] = Field("AgriSensa_Harvest_Reports", description="Nama folder di Google Drive")


class GoogleDriveStatusResponse(BaseModel):
    is_connected: bool
    mode: str
    webhook_url: Optional[str] = None
    client_email: Optional[str] = None
    folder_id: Optional[str] = None
    folder_name: str
    message: str


@router.get("/google-drive", response_model=ApiResponse[GoogleDriveStatusResponse])
def get_google_drive_status():
    """Mengambil status koneksi Google Drive saat ini."""
    is_conn = google_drive_service.is_authenticated
    mode = google_drive_service.integration_mode

    masked_webhook = None
    if settings.GOOGLE_DRIVE_WEBHOOK_URL:
        url = settings.GOOGLE_DRIVE_WEBHOOK_URL
        masked_webhook = url[:35] + "..." + url[-10:] if len(url) > 50 else url

    msg = "Google Drive terhubung dan siap digunakan." if is_conn else "Google Drive belum terhubung. Silakan masukkan URL Webhook Google Apps Script Anda."

    return ApiResponse(
        success=True,
        message="Status Google Drive berhasil diambil.",
        data=GoogleDriveStatusResponse(
            is_connected=is_conn,
            mode=mode,
            webhook_url=masked_webhook,
            client_email=google_drive_service.client_email,
            folder_id=settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
            folder_name=settings.GOOGLE_DRIVE_FOLDER_NAME,
            message=msg
        )
    )


@router.post("/google-drive/test", response_model=ApiResponse[dict])
def test_google_drive_connection(payload: GoogleDriveConfigRequest):
    """Menguji koneksi ke Google Drive (baik via Webhook ataupun Service Account)."""
    # 1. Uji Google Apps Script Webhook
    if payload.webhook_url and payload.webhook_url.strip():
        url = payload.webhook_url.strip()
        if not (url.startswith("https://script.google.com/") or url.startswith("http")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL Webhook tidak valid. Pastikan URL dimulai dengan 'https://script.google.com/macros/s/...'"
            )
        try:
            import httpx
            resp = httpx.post(
                url,
                json={"action": "ping", "message": "AgriSensa Connection Test"},
                follow_redirects=True,
                timeout=15.0
            )
            if resp.status_code == 200:
                return ApiResponse(
                    success=True,
                    message="Koneksi ke Google Apps Script Webhook BERHASIL!",
                    data={"mode": "apps_script_webhook", "status": "active", "url": url[:40] + "..."}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Webhook merespons dengan HTTP {resp.status_code}. Pastikan izin deployment diset 'Anyone'."
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gagal menghubungi Google Apps Script: {str(e)}"
            )

    # 2. Uji Service Account jika disediakan
    if payload.service_account_json and payload.service_account_json.strip():
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            info = json.loads(payload.service_account_json)
            client_email = info.get("client_email")
            if not client_email:
                raise ValueError("Berkas JSON tidak memiliki 'client_email'.")

            creds = service_account.Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/drive"]
            )
            service = build("drive", "v3", credentials=creds)
            about = service.about().get(fields="user").execute()
            user_name = about.get("user", {}).get("displayName", "Service Account")

            return ApiResponse(
                success=True,
                message=f"Koneksi Service Account berhasil: {client_email}",
                data={"client_email": client_email, "user_name": user_name}
            )
        except Exception as sa_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gagal koneksi Service Account: {str(sa_err)}"
            )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Harap masukkan URL Webhook Google Apps Script atau JSON Service Account."
    )


@router.post("/google-drive", response_model=ApiResponse[dict])
def save_google_drive_config(payload: GoogleDriveConfigRequest):
    """Menyimpan dan menerapkan konfigurasi Google Drive pada runtime aplikasi."""
    try:
        if payload.folder_name:
            settings.GOOGLE_DRIVE_FOLDER_NAME = payload.folder_name.strip()
        if payload.folder_id:
            settings.GOOGLE_DRIVE_ROOT_FOLDER_ID = payload.folder_id.strip()

        # Opsi Webhook
        if payload.webhook_url and payload.webhook_url.strip():
            settings.GOOGLE_DRIVE_WEBHOOK_URL = payload.webhook_url.strip()
            google_drive_service._init_client()
            return ApiResponse(
                success=True,
                message="Konfigurasi Google Apps Script Webhook berhasil disimpan dan diaktifkan!",
                data={
                    "mode": "apps_script_webhook",
                    "is_connected": True,
                    "folder_name": settings.GOOGLE_DRIVE_FOLDER_NAME
                }
            )

        # Opsi Service Account
        if payload.service_account_json and payload.service_account_json.strip():
            settings.GOOGLE_SERVICE_ACCOUNT_JSON = payload.service_account_json.strip()
            google_drive_service._init_client()
            return ApiResponse(
                success=True,
                message="Konfigurasi Service Account berhasil disimpan dan diaktifkan.",
                data={
                    "mode": "service_account",
                    "is_connected": True,
                    "client_email": google_drive_service.client_email
                }
            )

        raise ValueError("Harap masukkan URL Webhook atau JSON Service Account.")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal menyimpan konfigurasi: {str(e)}"
        )


@router.post("/google-drive/test-upload", response_model=ApiResponse[dict])
def test_upload_to_drive():
    """Menguji coba upload berkas pengujian langsung ke Google Drive."""
    if not google_drive_service.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Drive belum terkonfigurasi. Silakan simpan URL Webhook Google Apps Script terlebih dahulu."
        )

    try:
        test_content = (
            f"🌾 AgriSensa Harvest Intelligence - Uji Coba Koneksi Google Drive\n"
            f"Waktu Uji: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} WIB\n"
            f"Status: Berhasil Terkoneksi ke Google Drive Anda!\n"
        )

        res = google_drive_service.upload_test_content(
            text_content=test_content,
            filename="AgriSensa_Connection_Test.txt"
        )

        return ApiResponse(
            success=True,
            message="Berkas uji coba 'AgriSensa_Connection_Test.txt' BERHASIL diunggah ke Google Drive Anda!",
            data=res
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gagal mengunggah berkas uji coba: {str(e)}"
        )


# =====================================================================
# NOTIFICATION & WEBHOOK CONFIGURATION
# =====================================================================

from app.services.notification_service import notification_service


class NotificationConfigRequest(BaseModel):
    is_enabled: Optional[bool] = Field(True, description="Status aktifkan notifikasi")
    webhook_url: Optional[str] = Field(None, description="URL Webhook (WhatsApp API / Telegram / Slack / Discord / n8n)")
    telegram_bot_token: Optional[str] = Field(None, description="Bot Token Telegram")
    telegram_chat_id: Optional[str] = Field(None, description="Chat ID Telegram")


from app.services.clerk_auth import get_current_user, AuthUser
from fastapi import Depends


@router.get("/notifications", response_model=ApiResponse[dict])
def get_notification_config(current_user: AuthUser = Depends(get_current_user)):
    """Mengambil konfigurasi notifikasi saat ini."""
    from app.services.db import db_manager
    user_conf = db_manager.get_notification_config(user_id=current_user.user_id)
    webhook_val = user_conf.get("webhook_url") or notification_service.webhook_url

    masked_url = None
    if webhook_val:
        masked_url = webhook_val[:25] + "..." + webhook_val[-8:] if len(webhook_val) > 35 else webhook_val

    return ApiResponse(
        success=True,
        message="Konfigurasi notifikasi berhasil diambil.",
        data={
            "is_enabled": user_conf.get("is_enabled", notification_service.is_enabled),
            "webhook_url": masked_url,
            "raw_webhook_url": webhook_val,
            "has_telegram": bool(user_conf.get("telegram_token") or (notification_service.telegram_token and notification_service.telegram_chat_id))
        }
    )


@router.post("/notifications", response_model=ApiResponse[dict])
def save_notification_config(
    payload: NotificationConfigRequest,
    current_user: AuthUser = Depends(get_current_user)
):
    """Menyimpan konfigurasi URL Webhook / WhatsApp ke database per akun terdaftar."""
    from app.services.db import db_manager

    is_enabled = payload.is_enabled if payload.is_enabled is not None else notification_service.is_enabled
    webhook_url = payload.webhook_url.strip() if payload.webhook_url is not None else notification_service.webhook_url
    telegram_token = payload.telegram_bot_token.strip() if payload.telegram_bot_token is not None else notification_service.telegram_token
    telegram_chat_id = payload.telegram_chat_id.strip() if payload.telegram_chat_id is not None else notification_service.telegram_chat_id

    # Persist to real database scoped to this user
    db_manager.save_notification_config({
        "is_enabled": is_enabled,
        "webhook_url": webhook_url,
        "telegram_token": telegram_token,
        "telegram_chat_id": telegram_chat_id
    }, user_id=current_user.user_id)

    return ApiResponse(
        success=True,
        message="Konfigurasi notifikasi WhatsApp / Webhook berhasil disimpan secara permanen pada akun Anda.",
        data={
            "is_enabled": is_enabled,
            "webhook_url": webhook_url,
            "status": "active" if is_enabled else "disabled"
        }
    )


class NotificationTestRequest(BaseModel):
    webhook_url: Optional[str] = Field(None, description="URL Webhook pengujian (opsional)")
    custom_message: Optional[str] = Field(None, description="Pesan khusus uji coba")


@router.post("/notifications/test", response_model=ApiResponse[dict])
def test_notification_webhook(payload: NotificationTestRequest):
    """Mengirim pesan uji coba ke Webhook / WhatsApp."""
    result = notification_service.send_test_message(
        target_webhook=payload.webhook_url,
        custom_message=payload.custom_message
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Gagal mengirim notifikasi uji coba.")
        )
    return ApiResponse(
        success=True,
        message=result.get("message", "Notifikasi uji coba berhasil dikirim!"),
        data=result
    )


