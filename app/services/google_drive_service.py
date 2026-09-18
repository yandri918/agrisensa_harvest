import io
import os
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from app.config import settings
from app.schemas.harvest import HarvestRecordResponse

logger = logging.getLogger("agrisensa.drive")

# Google Drive API Scopes - Menggunakan full scope agar dapat membaca dan menulis ke folder yang dibagikan oleh user
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]


class GoogleDriveService:
    """Service untuk integrasi langsung dan andal dengan Google Drive API v3."""

    def __init__(self):
        self._service = None
        self._is_authenticated = False
        self._client_email = None
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
                    self._client_email = info.get("client_email")
                    creds = service_account.Credentials.from_service_account_info(
                        info, scopes=SCOPES
                    )
                    logger.info(f"Google Drive API initialized via GOOGLE_SERVICE_ACCOUNT_JSON ({self._client_email}).")
                except Exception as err:
                    logger.warning(f"Gagal mem-parsing GOOGLE_SERVICE_ACCOUNT_JSON: {err}")

            # 2. Coba baca dari file JSON lokal jika kredensial belum ada
            if not creds and settings.GOOGLE_SERVICE_ACCOUNT_FILE:
                if os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
                    try:
                        with open(settings.GOOGLE_SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            self._client_email = info.get("client_email")
                        creds = service_account.Credentials.from_service_account_file(
                            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
                        )
                        logger.info(f"Google Drive API initialized via file: {settings.GOOGLE_SERVICE_ACCOUNT_FILE}")
                    except Exception as f_err:
                        logger.warning(f"Gagal membaca file service account lokal: {f_err}")

            if creds:
                self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
                self._is_authenticated = True
            else:
                logger.info("Google Drive Service Account belum dikonfigurasi. Berjalan dalam mode simulasi.")
                self._is_authenticated = False
                self._client_email = None

        except ImportError:
            logger.warning("Pustaka google-api-python-client atau google-auth belum terpasang.")
            self._is_authenticated = False
        except Exception as e:
            logger.error(f"Kesalahan inisialisasi Google Drive API: {e}")
            self._is_authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._is_authenticated

    @property
    def client_email(self) -> Optional[str]:
        return self._client_email

    def get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Mencari atau membuat folder baru di Google Drive."""
        if not self._is_authenticated or not self._service:
            return None

        try:
            # Query pencarian folder
            q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                q += f" and '{parent_id}' in parents"

            response = self._service.files().list(
                q=q,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
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
                body=folder_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()
            return folder.get("id")

        except Exception as e:
            logger.error(f"Gagal membuat/mencari folder '{folder_name}' di Google Drive: {e}")
            # Fallback ke parent_id jika sub-folder gagal dibuat
            return parent_id

    def generate_html_report(self, record: HarvestRecordResponse) -> str:
        """Menghasilkan dokumen laporan HTML yang rapi dan estetis untuk dibuka langsung di Google Drive."""
        kpi = record.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None

        grades_rows = ""
        if record.quality_grades:
            for g in record.quality_grades:
                grades_rows += f"<tr><td>Grade {g.grade}</td><td>{g.quantity_kg:,.1f} kg</td><td>Rp {g.price_per_kg:,.0f}</td><td>{g.notes or '-'}</td></tr>"
        else:
            grades_rows = "<tr><td colspan='4'>Tidak ada rincian grade khusus</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Laporan Hasil Panen - {record.commodity}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; line-height: 1.6; background-color: #f8fafc; }}
    .container {{ max-width: 800px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }}
    .header {{ border-bottom: 2px solid #10b981; padding-bottom: 20px; margin-bottom: 28px; display: flex; justify-content: space-between; align-items: center; }}
    .brand {{ font-size: 24px; font-weight: 800; color: #059669; }}
    .meta {{ font-size: 13px; color: #64748b; text-align: right; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }}
    .kpi-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; padding: 16px; border-radius: 8px; text-align: center; }}
    .kpi-val {{ font-size: 20px; font-weight: 700; color: #059669; }}
    .kpi-lbl {{ font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 10px 14px; text-align: left; }}
    th {{ background: #f1f5f9; color: #475569; }}
    .badge {{ display: inline-block; padding: 4px 10px; background: #dcfce7; color: #15803d; border-radius: 999px; font-weight: 600; font-size: 12px; }}
    .footer {{ margin-top: 36px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="brand">🌾 AgriSensa Harvest Intelligence</div>
        <p style="margin: 4px 0 0; color: #64748b; font-size: 14px;">Laporan Resmi Rekapitulasi & Analisis Hasil Panen</p>
      </div>
      <div class="meta">
        <strong>Status: <span class="badge">{record.status.upper()}</span></strong><br>
        Tgl Cetak: {datetime.now().strftime('%d %B %Y %H:%M')} WIB
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi-box">
        <div class="kpi-val">{record.harvest_quantity_kg:,.0f} kg</div>
        <div class="kpi-lbl">Total Hasil Panen</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-val">{prod_kpi.productivity_kg_per_ha:,.1f} kg/ha</div>
        <div class="kpi-lbl">Produktivitas</div>
      </div>
      <div class="kpi-box">
        <div class="kpi-val">Rp {record.net_profit:,.0f}</div>
        <div class="kpi-lbl">Keuntungan Bersih</div>
      </div>
    </div>

    <h3>📋 Identitas Panen & Budidaya</h3>
    <table>
      <tr><th width="30%">Komoditas / Varietas</th><td><strong>{record.commodity}</strong> ({record.variety or 'Standar'})</td></tr>
      <tr><th>ID Kebun / Petani</th><td>{record.farm_id} / {record.farmer_id}</td></tr>
      <tr><th>Luas Lahan</th><td>{record.land_area_ha} ha ({record.original_land_area} {record.original_land_area_unit})</td></tr>
      <tr><th>Tanggal Tanam & Panen</th><td>{record.planting_date} s/d {record.harvest_date} (Panen Ke-{record.harvest_sequence})</td></tr>
      <tr><th>Kanal Penjualan</th><td>{record.sales_channel or '-'}</td></tr>
    </table>

    <h3>💰 Analisis Finansial & Mutu</h3>
    <table>
      <tr><th width="30%">Pendapatan Kotor (Omset)</th><td>Rp {record.gross_revenue:,.0f} (Rp {record.selling_price_per_kg:,.0f}/kg)</td></tr>
      <tr><th>Total Biaya Produksi</th><td>Rp {record.total_production_cost:,.0f}</td></tr>
      <tr><th>Return on Investment (ROI)</th><td><strong>{econ_kpi.roi_percent if econ_kpi else 0:.2f}%</strong></td></tr>
      <tr><th>Break-Even Price (BEP)</th><td>Rp {econ_kpi.break_even_price_idr if econ_kpi else 0:,.2f} / kg</td></tr>
      <tr><th>Tingkat Kerusakan (Loss Rate)</th><td>{prod_kpi.loss_rate_percent if prod_kpi else 0:.2f}% ({record.damaged_quantity_kg:,.1f} kg)</td></tr>
    </table>

    <h3>🎯 Rincian Mutu / Grade</h3>
    <table>
      <thead><tr><th>Grade</th><th>Kuantitas</th><th>Harga Satuan</th><th>Catatan</th></tr></thead>
      <tbody>{grades_rows}</tbody>
    </table>

    <div class="footer">
      Dokumen ini dihasilkan secara otomatis oleh <strong>AgriSensa AI & Harvest Intelligence Engine</strong>.<br>
      ID Panen: <code>{record.harvest_id}</code> | Idempotency: <code>{record.idempotency_key or '-'}</code>
    </div>
  </div>
</body>
</html>"""

    def upload_harvest_report(self, record: HarvestRecordResponse) -> Dict[str, Any]:
        """
        Membuat berkas laporan panen (format HTML visual + JSON) dan mengunggahnya ke Google Drive.
        """
        year_str = str(record.harvest_date.year)
        commodity_clean = record.commodity.replace(" ", "_")
        filename_html = f"AgriSensa_Report_{commodity_clean}_{record.farm_id}_{record.harvest_date}_{record.harvest_id[:8]}.html"

        html_content = self.generate_html_report(record)
        content_bytes = html_content.encode("utf-8")

        # Jika kredensial belum ada, berikan respons simulasi yang informatif
        if not self._is_authenticated or not self._service:
            return {
                "success": False,
                "mode": "simulation",
                "file_id": None,
                "file_name": filename_html,
                "folder_path": f"AgriSensa/{year_str}/{record.commodity}",
                "web_view_link": None,
                "message": "Google Drive belum terhubung. Silakan klik tombol '⚙️ Google Drive' di header dan masukkan Service Account JSON Anda."
            }

        try:
            from googleapiclient.http import MediaIoBaseUpload

            # 1. Tentukan target folder
            root_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip() if settings.GOOGLE_DRIVE_ROOT_FOLDER_ID else None
            
            # Jika tidak ada root_id spesifik, buat/cari folder default
            if not root_id:
                root_id = self.get_or_create_folder(settings.GOOGLE_DRIVE_FOLDER_NAME)

            # Buat sub-folder tahun & komoditas
            year_folder_id = self.get_or_create_folder(year_str, parent_id=root_id) or root_id
            target_folder_id = self.get_or_create_folder(record.commodity, parent_id=year_folder_id) or year_folder_id

            # 2. Upload berkas ke Google Drive
            file_metadata = {
                "name": filename_html,
                "mimeType": "text/html"
            }
            if target_folder_id:
                file_metadata["parents"] = [target_folder_id]

            media = MediaIoBaseUpload(
                io.BytesIO(content_bytes),
                mimetype="text/html",
                resumable=True
            )

            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink",
                supportsAllDrives=True
            ).execute()

            file_id = file.get("id")
            web_view_link = file.get("webViewLink")

            # 3. Buat izin akses publik agar tautan bisa langsung dibuka
            try:
                self._service.permissions().create(
                    fileId=file_id,
                    body={"type": "anyone", "role": "reader"},
                    supportsAllDrives=True
                ).execute()
            except Exception as perm_err:
                logger.warning(f"Izin publik tidak dapat diterapkan: {perm_err}")

            return {
                "success": True,
                "mode": "live_google_drive",
                "file_id": file_id,
                "file_name": file.get("name"),
                "folder_path": f"{settings.GOOGLE_DRIVE_FOLDER_NAME}/{year_str}/{record.commodity}",
                "web_view_link": web_view_link,
                "message": f"Berhasil diunggah ke Google Drive di folder '{record.commodity}'."
            }

        except Exception as err:
            logger.error(f"Gagal mengunggah laporan panen ke Google Drive: {err}")
            return {
                "success": False,
                "mode": "error",
                "error": str(err),
                "message": f"Gagal mengunggah ke Google Drive: {err}. Pastikan folder Drive telah di-share ke email Service Account."
            }


# Singleton instance
google_drive_service = GoogleDriveService()
