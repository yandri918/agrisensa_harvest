import logging
import httpx
from typing import Optional, Dict, Any
from app.config import settings
from app.services.ai_insight_service import ai_insight_service

logger = logging.getLogger("agrisensa.notifications")


class NotificationService:
    """Service untuk pengiriman notifikasi otomatis (WhatsApp, Telegram, Webhook) saat panen tercatat."""

    def __init__(self):
        self.webhook_url: str = settings.WEBHOOK_URL if hasattr(settings, "WEBHOOK_URL") else ""
        self.telegram_token: str = settings.TELEGRAM_BOT_TOKEN if hasattr(settings, "TELEGRAM_BOT_TOKEN") else ""
        self.telegram_chat_id: str = settings.TELEGRAM_CHAT_ID if hasattr(settings, "TELEGRAM_CHAT_ID") else ""
        self.is_enabled: bool = True

    def build_harvest_message(self, record: Any) -> str:
        ai_eval = ai_insight_service.evaluate_harvest_record(record)
        kpi = record.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None

        prod_val = prod_kpi.productivity_kg_per_ha if prod_kpi else (record.harvest_quantity_kg / record.land_area_ha if record.land_area_ha > 0 else 0)
        roi_val = econ_kpi.roi_percent if econ_kpi else (record.net_profit / record.total_production_cost * 100 if record.total_production_cost > 0 else 0)
        loss_val = prod_kpi.loss_rate_percent if prod_kpi else (record.damaged_quantity_kg / record.harvest_quantity_kg * 100 if record.harvest_quantity_kg > 0 else 0)
        marketable_pct = 100.0 - loss_val

        delta_pct = ai_eval.get("productivity_delta_percent", 0)
        delta_str = f"+{delta_pct:.1f}%" if delta_pct > 0 else f"{delta_pct:.1f}%"
        stars = ai_eval.get("rating_stars", "⭐⭐⭐⭐")
        status_label = ai_eval.get("status_label", "OPTIMAL")

        message = (
            f"🌾 *AGRISENSA HARVEST INTELLIGENCE* 🌾\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ *Laporan Panen Baru Masuk!*\n\n"
            f"🌱 *Komoditas*: {record.commodity} ({record.variety or 'Standar'})\n"
            f"📍 *Kebun / Petani*: `{record.farm_id}` / `{record.farmer_id}`\n"
            f"📅 *Tanggal Panen*: {record.harvest_date} (Panen Ke-{record.harvest_sequence})\n"
            f"📐 *Luas Lahan*: {record.land_area_ha} ha\n\n"
            f"⚖️ *HASIL & MUTU PANEN*:\n"
            f"• Total Panen : {record.harvest_quantity_kg:,.0f} kg\n"
            f"• Layak Jual  : {record.marketable_quantity_kg:,.0f} kg ({marketable_pct:.1f}%)\n"
            f"• Rusak/Afkir : {record.damaged_quantity_kg:,.0f} kg (Loss: {loss_val:.1f}%)\n\n"
            f"⚡ *PRODUKTIVITAS & AI BENCHMARK*:\n"
            f"• Produktivitas: {prod_val:,.0f} kg/ha ({delta_str} vs Acuan)\n"
            f"• Evaluasi AI : {stars} {status_label}\n\n"
            f"💰 *KINERJA FINANSIAL*:\n"
            f"• Omset Kotor : Rp {record.gross_revenue:,.0f}\n"
            f"• Biaya Total : Rp {record.total_production_cost:,.0f}\n"
            f"• Laba Bersih : Rp {record.net_profit:,.0f} (ROI: {roi_val:.1f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📄 *ID Panen*: `{record.harvest_id}`"
        )
        return message

    def send_harvest_notification(self, record: Any) -> Dict[str, Any]:
        """Mengirim notifikasi ke Webhook / Telegram / WhatsApp."""
        if not self.is_enabled:
            logger.info("Notifikasi dimatikan.")
            return {"status": "skipped", "reason": "disabled"}

        message_text = self.build_harvest_message(record)
        results = {}

        # 1. Dispatch ke Generic / WhatsApp Webhook
        target_webhook = self.webhook_url or (settings.N8N_WEBHOOK_HARVEST_CREATED if hasattr(settings, "N8N_WEBHOOK_HARVEST_CREATED") else "")
        if target_webhook and target_webhook.strip():
            try:
                payload = {
                    "event": "harvest.created",
                    "harvest_id": record.harvest_id,
                    "commodity": record.commodity,
                    "farm_id": record.farm_id,
                    "farmer_id": record.farmer_id,
                    "harvest_date": str(record.harvest_date),
                    "harvest_quantity_kg": record.harvest_quantity_kg,
                    "net_profit": record.net_profit,
                    "formatted_message": message_text,
                    # WhatsApp gateway payload compatibility (Fonnte/Waha/Wablas)
                    "message": message_text,
                    "content": message_text,
                    "text": message_text
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(target_webhook.strip(), json=payload)
                    results["webhook"] = {
                        "status_code": resp.status_code,
                        "success": resp.status_code in [200, 201, 202, 204]
                    }
                    logger.info(f"Webhook notification sent to {target_webhook}: HTTP {resp.status_code}")
            except Exception as e:
                logger.error(f"Error dispatching webhook notification: {str(e)}")
                results["webhook"] = {"success": False, "error": str(e)}

        # 2. Dispatch ke Telegram Bot
        if self.telegram_token and self.telegram_chat_id:
            try:
                tg_url = f"https://api.telegram.org/bot{self.telegram_token.strip()}/sendMessage"
                tg_payload = {
                    "chat_id": self.telegram_chat_id.strip(),
                    "text": message_text,
                    "parse_mode": "Markdown"
                }
                with httpx.Client(timeout=10.0) as client:
                    tg_resp = client.post(tg_url, json=tg_payload)
                    results["telegram"] = {
                        "status_code": tg_resp.status_code,
                        "success": tg_resp.status_code == 200
                    }
                    logger.info(f"Telegram notification sent: HTTP {tg_resp.status_code}")
            except Exception as tg_err:
                logger.error(f"Error sending Telegram notification: {str(tg_err)}")
                results["telegram"] = {"success": False, "error": str(tg_err)}

        return results

    def send_test_message(self, target_webhook: Optional[str] = None, custom_message: Optional[str] = None) -> Dict[str, Any]:
        """Uji coba pengiriman pesan notifikasi."""
        url = target_webhook or self.webhook_url
        if not url or not url.strip():
            return {
                "success": False,
                "message": "Webhook URL belum diisi. Silakan masukkan Webhook URL terlebih dahulu."
            }

        text = custom_message or (
            "🌾 *AGRISENSA HARVEST INTELLIGENCE - UJI NOTIFIKASI* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Sistem notifikasi otomatis WhatsApp/Webhook berhasil terkoneksi!\n"
            "Setiap ada data panen baru yang dicatat, Anda akan menerima ringkasan otomatis di kanal ini."
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url.strip(),
                    json={
                        "event": "test.ping",
                        "message": text,
                        "content": text,
                        "text": text
                    }
                )
                return {
                    "success": resp.status_code in [200, 201, 202, 204],
                    "status_code": resp.status_code,
                    "message": f"Webhook berhasil diuji (HTTP {resp.status_code})"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Gagal mengirim notifikasi uji coba: {str(e)}"
            }


notification_service = NotificationService()
