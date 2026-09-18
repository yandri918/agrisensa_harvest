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
    """Service untuk integrasi Google Drive (Mendukung Apps Script Webhook & Service Account)."""

    def __init__(self):
        self._service = None
        self._is_authenticated = False
        self._client_email = None
        self._init_client()

    def _init_client(self):
        """Inisialisasi Google Drive client."""
        # 1. Periksa apakah Webhook URL telah diset
        if settings.GOOGLE_DRIVE_WEBHOOK_URL and settings.GOOGLE_DRIVE_WEBHOOK_URL.startswith("http"):
            self._is_authenticated = True
            logger.info("Google Drive aktif via Google Apps Script Webhook.")
            return

        # 2. Coba Service Account jika ada
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = None
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

            if not creds and settings.GOOGLE_SERVICE_ACCOUNT_FILE:
                if os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
                    try:
                        with open(settings.GOOGLE_SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            self._client_email = info.get("client_email")
                        creds = service_account.Credentials.from_service_account_file(
                            settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
                        )
                    except Exception as f_err:
                        logger.warning(f"Gagal membaca file service account lokal: {f_err}")

            if creds:
                self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
                self._is_authenticated = True
            else:
                self._is_authenticated = False
                self._client_email = None

        except ImportError:
            self._is_authenticated = False
        except Exception as e:
            logger.error(f"Kesalahan inisialisasi Google Drive: {e}")
            self._is_authenticated = False

    @property
    def is_authenticated(self) -> bool:
        if bool(settings.GOOGLE_DRIVE_WEBHOOK_URL and settings.GOOGLE_DRIVE_WEBHOOK_URL.startswith("http")):
            return True
        return self._is_authenticated

    @property
    def client_email(self) -> Optional[str]:
        return self._client_email

    @property
    def integration_mode(self) -> str:
        if bool(settings.GOOGLE_DRIVE_WEBHOOK_URL and settings.GOOGLE_DRIVE_WEBHOOK_URL.startswith("http")):
            return "apps_script_webhook"
        elif self._service:
            return "service_account"
        return "unconfigured"

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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap');
    body {{ font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif; margin: 30px; color: #1e293b; line-height: 1.5; background-color: #f8fafc; }}
    .container {{ max-width: 860px; margin: 0 auto; background: #ffffff; padding: 36px 42px; border-radius: 12px; box-shadow: 0 4px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
    
    .kop-container {{ display: flex; justify-content: space-between; align-items: center; gap: 20px; padding-bottom: 14px; }}
    .kop-brand-wrap {{ display: flex; align-items: center; gap: 16px; }}
    .kop-logo-box {{ width: 56px; height: 56px; border-radius: 12px; background: linear-gradient(135deg, #059669, #0d9488); display: flex; align-items: center; justify-content: center; font-size: 28px; color: #ffffff; flex-shrink: 0; }}
    .kop-brand-text h1 {{ font-family: 'Outfit', sans-serif; font-size: 19px; font-weight: 800; color: #065f46; letter-spacing: 0.02em; text-transform: uppercase; line-height: 1.2; margin: 0; }}
    .kop-brand-text .kop-sub1 {{ font-size: 11px; font-weight: 700; color: #047857; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }}
    .kop-brand-text .kop-sub2 {{ font-size: 10.5px; color: #64748b; margin-top: 2px; }}
    .kop-meta-box {{ text-align: right; font-size: 11px; color: #334155; border-left: 2px solid #e2e8f0; padding-left: 16px; flex-shrink: 0; }}
    .kop-badge {{ display: inline-block; padding: 3px 9px; background: #ecfdf5; color: #047857; font-weight: 700; border-radius: 6px; font-size: 10.5px; text-transform: uppercase; border: 1px solid #a7f3d0; margin-bottom: 4px; }}
    .kop-double-divider {{ border-top: 3px solid #047857; border-bottom: 1px solid #10b981; height: 3px; margin-bottom: 22px; }}

    .doc-title-banner {{ text-align: center; margin-bottom: 20px; }}
    .doc-title-banner h2 {{ font-family: 'Outfit', sans-serif; font-size: 15px; font-weight: 800; color: #0f172a; text-transform: uppercase; letter-spacing: 0.05em; }}
    .doc-title-banner p {{ font-size: 11.5px; color: #64748b; margin-top: 2px; }}

    .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 22px; }}
    .kpi-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px 14px; border-radius: 8px; text-align: center; }}
    .kpi-val {{ font-size: 18px; font-weight: 700; color: #059669; }}
    .kpi-lbl {{ font-size: 10px; color: #64748b; text-transform: uppercase; margin-top: 3px; font-weight: 700; }}

    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 12px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
    th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
    .footer {{ margin-top: 28px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 10.5px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="kop-container">
      <div class="kop-brand-wrap">
        <div class="kop-logo-box">🌾</div>
        <div class="kop-brand-text">
          <h1>AGRISENSA HARVEST INTELLIGENCE</h1>
          <div class="kop-sub1">Sistem Cerdas Pencatatan & Analitik Rekapitulasi Panen</div>
          <div class="kop-sub2">Dokumen Resmi Laporan Panen Terintegrasi Google Drive</div>
        </div>
      </div>
      <div class="kop-meta-box">
        <div><span class="kop-badge">{record.status.upper()}</span></div>
        <div><strong>No:</strong> <code>HARV-{record.harvest_id[:8].upper()}</code></div>
        <div><strong>Tgl Cetak:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')} WIB</div>
      </div>
    </div>

    <div class="kop-double-divider"></div>

    <div class="doc-title-banner">
      <h2>LEMBAR LAPORAN REKAPITULASI & EVALUASI PANEN</h2>
      <p>Komoditas: <strong>{record.commodity}</strong> (Varietas: {record.variety or 'Standar'}) &bull; Periode Panen: {record.harvest_date}</p>
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
        Membuat berkas laporan panen (format HTML visual) dan mengunggahnya ke Google Drive.
        """
        year_str = str(record.harvest_date.year)
        commodity_clean = record.commodity.replace(" ", "_")
        filename_html = f"AgriSensa_Report_{commodity_clean}_{record.farm_id}_{record.harvest_date}_{record.harvest_id[:8]}.html"

        html_content = self.generate_html_report(record)

        # 1. Jika terhubung via Google Apps Script Webhook (Metode Simpel & Direkomendasikan)
        if settings.GOOGLE_DRIVE_WEBHOOK_URL and settings.GOOGLE_DRIVE_WEBHOOK_URL.startswith("http"):
            try:
                import httpx
                payload = {
                    "action": "upload_report",
                    "filename": filename_html,
                    "content": html_content,
                    "folder_name": settings.GOOGLE_DRIVE_FOLDER_NAME,
                    "commodity": record.commodity,
                    "year": year_str,
                    "harvest_id": record.harvest_id
                }
                resp = httpx.post(
                    settings.GOOGLE_DRIVE_WEBHOOK_URL,
                    json=payload,
                    follow_redirects=True,
                    timeout=25.0
                )
                if resp.status_code == 200:
                    res_data = resp.json()
                    if res_data.get("success"):
                        return {
                            "success": True,
                            "mode": "apps_script_webhook",
                            "file_id": res_data.get("file_id"),
                            "file_name": res_data.get("file_name", filename_html),
                            "folder_path": f"{settings.GOOGLE_DRIVE_FOLDER_NAME}/{year_str}/{record.commodity}",
                            "web_view_link": res_data.get("web_view_link"),
                            "message": f"Berhasil diunggah ke Google Drive pribadi Anda di folder '{settings.GOOGLE_DRIVE_FOLDER_NAME}'."
                        }
                    else:
                        raise Exception(res_data.get("error", "Error pada script Google Drive"))
                else:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as w_err:
                logger.error(f"Gagal upload via Apps Script Webhook: {w_err}")
                return {
                    "success": False,
                    "mode": "error",
                    "error": str(w_err),
                    "message": f"Gagal mengunggah ke Google Drive via Webhook: {w_err}"
                }

        # 2. Jika kredensial belum ada sama sekali
        if not self._is_authenticated or not self._service:
            return {
                "success": False,
                "mode": "unconfigured",
                "file_id": None,
                "file_name": filename_html,
                "folder_path": f"AgriSensa/{year_str}/{record.commodity}",
                "web_view_link": None,
                "message": "Google Drive belum terhubung. Silakan klik tombol '☁️ Google Drive' di header dan masukkan URL Webhook Google Apps Script Anda."
            }

        # 3. Mode Service Account GCP (Fallback)
        try:
            from googleapiclient.http import MediaIoBaseUpload
            content_bytes = html_content.encode("utf-8")

            root_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip() if settings.GOOGLE_DRIVE_ROOT_FOLDER_ID else None
            if not root_id:
                root_id = self.get_or_create_folder(settings.GOOGLE_DRIVE_FOLDER_NAME)

            year_folder_id = self.get_or_create_folder(year_str, parent_id=root_id) or root_id
            target_folder_id = self.get_or_create_folder(record.commodity, parent_id=year_folder_id) or year_folder_id

            file_metadata = {
                "name": filename_html,
                "mimeType": "text/html"
            }
            if target_folder_id:
                file_metadata["parents"] = [target_folder_id]

            media = MediaIoBaseUpload(io.BytesIO(content_bytes), mimetype="text/html", resumable=True)
            file = self._service.files().create(
                body=file_metadata, media_body=media, fields="id, name, webViewLink, webContentLink", supportsAllDrives=True
            ).execute()

            file_id = file.get("id")
            web_view_link = file.get("webViewLink")

            try:
                self._service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}, supportsAllDrives=True).execute()
            except Exception:
                pass

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
                "message": f"Gagal mengunggah ke Google Drive: {err}"
            }

    def upload_test_content(self, text_content: str, filename: str = "AgriSensa_Connection_Test.txt") -> Dict[str, Any]:
        """Menguji coba upload berkas pengujian ke Google Drive."""
        if settings.GOOGLE_DRIVE_WEBHOOK_URL and settings.GOOGLE_DRIVE_WEBHOOK_URL.startswith("http"):
            import httpx
            payload = {
                "action": "upload_test",
                "filename": filename,
                "content": text_content,
                "folder_name": settings.GOOGLE_DRIVE_FOLDER_NAME
            }
            resp = httpx.post(
                settings.GOOGLE_DRIVE_WEBHOOK_URL,
                json=payload,
                follow_redirects=True,
                timeout=25.0
            )
            if resp.status_code == 200:
                res_data = resp.json()
                if res_data.get("success"):
                    return {
                        "file_id": res_data.get("file_id"),
                        "file_name": res_data.get("file_name", filename),
                        "web_view_link": res_data.get("web_view_link")
                    }
                else:
                    raise Exception(res_data.get("error", "Respon error dari Apps Script"))
            else:
                raise Exception(f"HTTP {resp.status_code}: {resp.text[:150]}")

        if not self._service:
            raise ValueError("Google Drive belum terkonfigurasi.")

        from googleapiclient.http import MediaIoBaseUpload
        root_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID.strip() if settings.GOOGLE_DRIVE_ROOT_FOLDER_ID else None
        if not root_id:
            root_id = self.get_or_create_folder(settings.GOOGLE_DRIVE_FOLDER_NAME)

        file_metadata = {"name": filename, "mimeType": "text/plain"}
        if root_id:
            file_metadata["parents"] = [root_id]

        media = MediaIoBaseUpload(io.BytesIO(text_content.encode("utf-8")), mimetype="text/plain", resumable=True)
        file = self._service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink", supportsAllDrives=True).execute()

        try:
            self._service.permissions().create(fileId=file.get("id"), body={"type": "anyone", "role": "reader"}, supportsAllDrives=True).execute()
        except Exception:
            pass

        return {
            "file_id": file.get("id"),
            "file_name": file.get("name"),
            "web_view_link": file.get("webViewLink")
        }


# Singleton instance
google_drive_service = GoogleDriveService()
