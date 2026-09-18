import io
import os
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from app.config import settings
from app.schemas.harvest import HarvestRecordResponse

logger = logging.getLogger("agrisensa.drive")

# Google Drive API Scopes
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveService:
    """Service untuk integrasi langsung dengan Google Drive API v3."""

    def __init__(self):
        self._service = None
        self._is_authenticated = False
        self._init_client()

    def _init_client(self):
        """Inisialisasi Google Drive client menggunakan Service Account credentials."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = None

            # 1. Coba baca dari string JSON di Environment (Railway / Cloud)
            if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                try:
                    info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                    creds = service_account.Credentials.from_service_account_info(
                        info, scopes=SCOPES
                    )
                    logger.info("Google Drive API initialized via GOOGLE_SERVICE_ACCOUNT_JSON.")
                except Exception as err:
                    logger.warning(f"Gagal mem-parsing GOOGLE_SERVICE_ACCOUNT_JSON: {err}")

            # 2. Coba baca dari file JSON lokal jika kredensial belum ada
            if not creds and settings.GOOGLE_SERVICE_ACCOUNT_FILE:
                if os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
                    creds = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
                    )
                    logger.info(f"Google Drive API initialized via file: {settings.GOOGLE_SERVICE_ACCOUNT_FILE}")

            if creds:
                self._service = build("drive", "v3", credentials=creds)
                self._is_authenticated = True
            else:
                logger.info("Google Drive Service Account belum dikonfigurasi. Berjalan dalam mode simulasi.")
                self._is_authenticated = False

        except ImportError:
            logger.warning("Pustaka google-api-python-client atau google-auth belum terpasang.")
            self._is_authenticated = False
        except Exception as e:
            logger.error(f"Kesalahan inisialisasi Google Drive API: {e}")
            self._is_authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Mencari atau membuat folder baru di Google Drive."""
        if not self._is_authenticated or not self._service:
            return "simulated-folder-id"

        try:
            # Query pencarian folder
            q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                q += f" and '{parent_id}' in parents"

            response = self._service.files().list(
                q=q, spaces="drive", fields="files(id, name)"
            ).execute()
            files = response.get("files", [])

            if files:
                return files[0].get("id")

            # Jika folder belum ada, buat folder baru
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            if parent_id:
                folder_metadata["parents"] = [parent_id]

            folder = self._service.files().create(
                body=folder_metadata, fields="id"
            ).execute()
            return folder.get("id")

        except Exception as e:
            logger.error(f"Gagal membuat folder '{folder_name}' di Google Drive: {e}")
            return None

    def upload_harvest_report(self, record: HarvestRecordResponse) -> Dict[str, Any]:
        """
        Membuat berkas ringkasan analitik panen dan mengunggahnya ke Google Drive.
        Folder tersusun otomatis: Root / [Tahun] / [Komoditas] /
        """
        year_str = str(record.harvest_date.year)
        commodity_clean = record.commodity.replace(" ", "_")
        filename = f"AgriSensa_Harvest_Report_{commodity_clean}_{record.farm_id}_{record.harvest_date}_{record.harvest_id[:8]}.json"

        # Generate dokumen ringkasan JSON yang rapi & terstruktur
        report_data = {
            "title": f"AgriSensa Harvest Intelligence Report - {record.commodity}",
            "generated_at": datetime.utcnow().isoformat(),
            "harvest_id": record.harvest_id,
            "idempotency_key": record.idempotency_key,
            "farm_profile": {
                "farm_id": record.farm_id,
                "farmer_id": record.farmer_id,
                "season_id": record.season_id,
                "location": record.location.model_dump() if record.location else None
            },
            "commodity_details": {
                "commodity": record.commodity,
                "variety": record.variety,
                "planting_date": str(record.planting_date),
                "harvest_date": str(record.harvest_date),
                "harvest_sequence": record.harvest_sequence,
                "land_area_ha": record.land_area_ha,
                "total_harvest_kg": record.harvest_quantity_kg,
                "marketable_kg": record.marketable_quantity_kg,
                "damaged_kg": record.damaged_quantity_kg,
            },
            "financials": {
                "selling_price_per_kg": record.selling_price_per_kg,
                "gross_revenue_idr": record.gross_revenue,
                "production_cost_idr": record.total_production_cost,
                "net_profit_idr": record.net_profit,
                "currency": record.currency,
                "sales_channel": record.sales_channel,
            },
            "calculated_kpis": record.kpi_summary.model_dump() if record.kpi_summary else None,
            "quality_grades": [g.model_dump() for g in record.quality_grades],
            "field_notes": record.notes
        }

        content_bytes = json.dumps(report_data, indent=2, ensure_ascii=False).encode("utf-8")

        # Jika kredensial belum ada, berikan respons simulasi yang informatif
        if not self._is_authenticated or not self._service:
            return {
                "success": True,
                "mode": "simulation",
                "file_id": f"sim-drive-{record.harvest_id[:8]}",
                "file_name": filename,
                "folder_path": f"AgriSensa/{year_str}/{record.commodity}",
                "web_view_link": "https://drive.google.com/",
                "message": "Dokumen siap. Atur variabel GOOGLE_SERVICE_ACCOUNT_JSON di Railway / .env untuk menghubungkan akun Google Drive aktif Anda."
            }

        try:
            from googleapiclient.http import MediaIoBaseUpload

            # 1. Buat hierarki folder: Root -> Tahun -> Komoditas
            root_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID or self.get_or_create_folder(settings.GOOGLE_DRIVE_FOLDER_NAME)
            year_folder_id = self.get_or_create_folder(year_str, parent_id=root_id)
            target_folder_id = self.get_or_create_folder(record.commodity, parent_id=year_folder_id)

            # 2. Upload file ke Google Drive
            file_metadata = {
                "name": filename,
                "parents": [target_folder_id] if target_folder_id else []
            }
            media = MediaIoBaseUpload(
                io.BytesIO(content_bytes),
                mimetype="application/json",
                resumable=True
            )

            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink"
            ).execute()

            # 3. Buat izin agar bisa dibuka
            try:
                self._service.permissions().create(
                    fileId=file.get("id"),
                    body={"type": "anyone", "role": "reader"}
                ).execute()
            except Exception:
                pass

            return {
                "success": True,
                "mode": "live_google_drive",
                "file_id": file.get("id"),
                "file_name": file.get("name"),
                "folder_path": f"AgriSensa/{year_str}/{record.commodity}",
                "web_view_link": file.get("webViewLink"),
                "web_content_link": file.get("webContentLink"),
                "message": f"Berhasil diunggah ke Google Drive di folder '{year_str}/{record.commodity}'."
            }

        except Exception as err:
            logger.error(f"Gagal mengunggah laporan panen ke Google Drive: {err}")
            return {
                "success": False,
                "mode": "error",
                "error": str(err),
                "message": f"Gagal mengunggah ke Google Drive: {err}"
            }


# Singleton instance
google_drive_service = GoogleDriveService()
