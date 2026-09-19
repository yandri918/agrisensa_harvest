import json
import os
import uuid
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.schemas.common import HarvestStatusEnum, DataSourceEnum
from app.schemas.harvest import (
    HarvestCreateRequest,
    HarvestUpdateRequest,
    HarvestRecordResponse,
)
from app.schemas.kpi import HarvestCalculatedKPIs
from app.services.normalizer import UnitNormalizer
from app.services.validator import HarvestValidator
from app.services.analytics_service import AnalyticsCalculator


DB_DIR = os.path.join(os.getcwd(), "data")
DB_PATH = os.path.join(DB_DIR, "agrisensa_harvest.db")


class DatabaseManager:
    """Manajer Database Relasional Persisten dengan Isolasi Pengguna Multi-Tenant & Dukungan Clerk."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()
        self._ensure_seed_data()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Membuat tabel skema database relasional dan migrasi kolom user_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tabel Master Pengguna Terdaftar (Clerk Users)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    image_url TEXT,
                    role TEXT DEFAULT 'farmer',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 2. Tabel Utama Rekapitulasi Panen
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS harvests (
                    harvest_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'USR-028',
                    idempotency_key TEXT UNIQUE,
                    farm_id TEXT NOT NULL,
                    farmer_id TEXT NOT NULL,
                    season_id TEXT,
                    commodity TEXT NOT NULL,
                    variety TEXT,
                    planting_date TEXT NOT NULL,
                    harvest_date TEXT NOT NULL,
                    harvest_sequence INTEGER DEFAULT 1,
                    land_area_ha REAL NOT NULL,
                    harvest_quantity_kg REAL NOT NULL,
                    marketable_quantity_kg REAL NOT NULL,
                    damaged_quantity_kg REAL NOT NULL,
                    original_land_area REAL NOT NULL,
                    original_land_area_unit TEXT NOT NULL,
                    original_quantity REAL NOT NULL,
                    original_quantity_unit TEXT NOT NULL,
                    selling_price_per_kg REAL NOT NULL,
                    currency TEXT DEFAULT 'IDR',
                    gross_revenue REAL NOT NULL,
                    total_production_cost REAL NOT NULL,
                    net_profit REAL NOT NULL,
                    sales_channel TEXT,
                    location_json TEXT,
                    quality_grades_json TEXT,
                    cost_details_json TEXT,
                    pest_disease_json TEXT,
                    damage_cause TEXT,
                    notes TEXT,
                    photo_urls_json TEXT,
                    status TEXT NOT NULL DEFAULT 'validated',
                    source TEXT NOT NULL DEFAULT 'api',
                    kpi_summary_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Migrasi: pastikan kolom user_id ada jika tabel sudah pernah dibuat sebelumnya
            cursor.execute("PRAGMA table_info(harvests)")
            columns = [row[1] for row in cursor.fetchall()]
            if "user_id" not in columns:
                cursor.execute("ALTER TABLE harvests ADD COLUMN user_id TEXT NOT NULL DEFAULT 'USR-028'")

            # 3. Indeks Kinerja Tinggi
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_user_id ON harvests(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_commodity ON harvests(commodity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_farm_id ON harvests(farm_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_farmer_id ON harvests(farmer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_harvest_date ON harvests(harvest_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_status ON harvests(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_idempotency ON harvests(idempotency_key)")

            # 4. Tabel Konfigurasi Sistem & Webhook
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.commit()

    def _ensure_seed_data(self):
        """Memastikan data awal terisi untuk akun default demo jika database masih kosong."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM harvests WHERE status != 'archived'")
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.provision_user_initial_harvests(
                    user_id="USR-028",
                    farmer_name="Mandor Kebun Banyumas",
                    email="mandor@agrisensa.ai"
                )

    def upsert_user(self, user) -> bool:
        """
        Menyimpan atau memperbarui profil pengguna terdaftar (Clerk).
        Jika akun ini baru pertama kali login, otomatis sediakan data starter personal.
        """
        user_id = user.user_id
        email = user.email or "petani@agrisensa.ai"
        full_name = user.full_name or "Petani Terdaftar"
        image_url = user.image_url or ""
        role = user.role or "farmer"
        now_iso = datetime.utcnow().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            existing = cursor.fetchone()

            if not existing:
                cursor.execute("""
                    INSERT INTO users (user_id, email, full_name, image_url, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, email, full_name, image_url, role, now_iso, now_iso))
                conn.commit()
                # Provision sample harvest records for this specific registered account
                self.provision_user_initial_harvests(user_id=user_id, farmer_name=full_name, email=email)
                return True
            else:
                cursor.execute("""
                    UPDATE users SET email = ?, full_name = ?, image_url = ?, role = ?, updated_at = ?
                    WHERE user_id = ?
                """, (email, full_name, image_url, role, now_iso, user_id))
                conn.commit()
                return False

    def provision_user_initial_harvests(self, user_id: str, farmer_name: str = "Petani", email: str = ""):
        """Menyediakan dataset panen awal siap pakai untuk akun pengguna baru."""
        sample_id = f"h-init-{user_id[-8:] if len(user_id) >= 8 else user_id}-001"
        sample_req = HarvestCreateRequest(
            idempotency_key=f"IDEMP-INIT-{user_id}-001",
            user_id=user_id,
            farm_id=f"FARM-{user_id[-4:].upper() if len(user_id) >= 4 else '001'}",
            farmer_id=user_id,
            season_id="SEASON-2026-01",
            commodity="Cabai Merah",
            variety="Lado F1",
            planting_date="2026-05-10",
            harvest_date="2026-09-17",
            harvest_sequence=1,
            land_area=0.5,
            land_area_unit="ha",
            harvest_quantity=3250,
            quantity_unit="kg",
            marketable_quantity=2980,
            damaged_quantity=270,
            selling_price_per_unit=42000,
            currency="IDR",
            production_cost=68500000,
            sales_channel="pasar_induk",
            damage_cause="Antraknosa pada sebagian buah",
            notes=f"Data panen inisialisasi akun terdaftar: {farmer_name} ({email})",
            location={
                "village": "Sumbang",
                "district": "Sumbang",
                "regency": "Banyumas",
                "province": "Jawa Tengah",
                "latitude": -7.343,
                "longitude": 109.244,
                "altitude_masl": 450.0,
            },
            quality_grades=[
                {"grade": "A", "quantity_kg": 1800, "price_per_kg": 45000},
                {"grade": "B", "quantity_kg": 850, "price_per_kg": 39000},
                {"grade": "C", "quantity_kg": 330, "price_per_kg": 30000},
            ],
            pest_disease=[
                {
                    "name": "Antraknosa",
                    "severity_percent": 8,
                    "treatment": "Sanitasi dan fungisida sesuai SOP",
                }
            ],
            source=DataSourceEnum.API,
        )
        try:
            self.insert_harvest(sample_req, custom_id=sample_id, initial_status=HarvestStatusEnum.APPROVED, user_id=user_id)
        except Exception:
            pass

    def _row_to_harvest_response(self, row: sqlite3.Row) -> HarvestRecordResponse:
        """Mengonversi row SQLite ke objek Pydantic HarvestRecordResponse."""
        kpi_dict = json.loads(row["kpi_summary_json"]) if row["kpi_summary_json"] else None
        kpi_obj = HarvestCalculatedKPIs(**kpi_dict) if kpi_dict else None

        row_keys = row.keys()
        user_id_val = row["user_id"] if "user_id" in row_keys else None

        return HarvestRecordResponse(
            harvest_id=row["harvest_id"],
            idempotency_key=row["idempotency_key"],
            user_id=user_id_val,
            farm_id=row["farm_id"],
            farmer_id=row["farmer_id"],
            season_id=row["season_id"],
            commodity=row["commodity"],
            variety=row["variety"],
            planting_date=datetime.strptime(row["planting_date"], "%Y-%m-%d").date(),
            harvest_date=datetime.strptime(row["harvest_date"], "%Y-%m-%d").date(),
            harvest_sequence=row["harvest_sequence"],
            land_area_ha=row["land_area_ha"],
            harvest_quantity_kg=row["harvest_quantity_kg"],
            marketable_quantity_kg=row["marketable_quantity_kg"],
            damaged_quantity_kg=row["damaged_quantity_kg"],
            original_land_area=row["original_land_area"],
            original_land_area_unit=row["original_land_area_unit"],
            original_quantity=row["original_quantity"],
            original_quantity_unit=row["original_quantity_unit"],
            selling_price_per_kg=row["selling_price_per_kg"],
            currency=row["currency"],
            gross_revenue=row["gross_revenue"],
            total_production_cost=row["total_production_cost"],
            net_profit=row["net_profit"],
            sales_channel=row["sales_channel"],
            location=json.loads(row["location_json"]) if row["location_json"] else None,
            quality_grades=json.loads(row["quality_grades_json"]) if row["quality_grades_json"] else [],
            cost_details=json.loads(row["cost_details_json"]) if row["cost_details_json"] else [],
            pest_disease=json.loads(row["pest_disease_json"]) if row["pest_disease_json"] else [],
            damage_cause=row["damage_cause"],
            notes=row["notes"],
            photo_urls=json.loads(row["photo_urls_json"]) if row["photo_urls_json"] else [],
            status=HarvestStatusEnum(row["status"]),
            source=DataSourceEnum(row["source"]),
            kpi_summary=kpi_obj,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_harvest_by_id(self, harvest_id: str, user_id: Optional[str] = None) -> Optional[HarvestRecordResponse]:
        """Mengambil data panen berdasarkan ID, opsional dibatasi user_id untuk isolasi keamanan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("SELECT * FROM harvests WHERE harvest_id = ? AND (user_id = ? OR user_id = 'USR-028')", (harvest_id, user_id))
            else:
                cursor.execute("SELECT * FROM harvests WHERE harvest_id = ?", (harvest_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_harvest_response(row)

    def get_harvest_by_idempotency(self, key: str, user_id: Optional[str] = None) -> Optional[HarvestRecordResponse]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM harvests WHERE idempotency_key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_harvest_response(row)

    def insert_harvest(
        self,
        payload: HarvestCreateRequest,
        custom_id: Optional[str] = None,
        initial_status: HarvestStatusEnum = HarvestStatusEnum.VALIDATED,
        user_id: Optional[str] = None
    ) -> Tuple[HarvestRecordResponse, bool]:
        owner_id = user_id or payload.user_id or payload.farmer_id or "USR-028"

        # Cek Idempotency Key
        if payload.idempotency_key:
            existing = self.get_harvest_by_idempotency(payload.idempotency_key, user_id=owner_id)
            if existing:
                return existing, False

        # Validasi
        validation_errors = HarvestValidator.validate_create_payload(payload)
        if validation_errors:
            raise ValueError(" | ".join(validation_errors))

        # Normalisasi
        land_area_ha = UnitNormalizer.normalize_area_to_ha(payload.land_area, payload.land_area_unit)
        total_kg = UnitNormalizer.normalize_weight_to_kg(payload.harvest_quantity, payload.quantity_unit)

        marketable_kg = total_kg
        damaged_kg = 0.0
        if payload.marketable_quantity is not None:
            marketable_kg = UnitNormalizer.normalize_weight_to_kg(payload.marketable_quantity, payload.quantity_unit)
        if payload.damaged_quantity is not None:
            damaged_kg = UnitNormalizer.normalize_weight_to_kg(payload.damaged_quantity, payload.quantity_unit)
        if payload.marketable_quantity is None and payload.damaged_quantity is not None:
            marketable_kg = max(0.0, total_kg - damaged_kg)

        selling_price_kg = payload.selling_price_per_unit
        if payload.quantity_unit.lower() == "ton":
            selling_price_kg = payload.selling_price_per_unit / 1000.0
        elif payload.quantity_unit.lower() == "kuintal":
            selling_price_kg = payload.selling_price_per_unit / 100.0
        elif payload.quantity_unit.lower() == "peti":
            selling_price_kg = payload.selling_price_per_unit / 30.0

        gross_revenue = marketable_kg * selling_price_kg
        net_profit = gross_revenue - payload.production_cost
        now_dt = datetime.utcnow()
        now_iso = now_dt.isoformat()
        harvest_id = custom_id or f"h{uuid.uuid4().hex[:31]}"

        # Hitung KPI
        kpi_summary = AnalyticsCalculator.calculate_all_kpis(
            harvest_id=harvest_id,
            commodity=payload.commodity,
            variety=payload.variety,
            harvest_date_str=str(payload.harvest_date),
            land_area_ha=land_area_ha,
            harvest_quantity_kg=total_kg,
            marketable_quantity_kg=marketable_kg,
            damaged_quantity_kg=damaged_kg,
            selling_price_per_kg=selling_price_kg,
            total_production_cost=payload.production_cost,
            quality_grades=payload.quality_grades
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO harvests (
                    harvest_id, user_id, idempotency_key, farm_id, farmer_id, season_id, commodity, variety,
                    planting_date, harvest_date, harvest_sequence, land_area_ha, harvest_quantity_kg,
                    marketable_quantity_kg, damaged_quantity_kg, original_land_area, original_land_area_unit,
                    original_quantity, original_quantity_unit, selling_price_per_kg, currency, gross_revenue,
                    total_production_cost, net_profit, sales_channel, location_json, quality_grades_json,
                    cost_details_json, pest_disease_json, damage_cause, notes, photo_urls_json,
                    status, source, kpi_summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                harvest_id,
                owner_id,
                payload.idempotency_key,
                payload.farm_id,
                payload.farmer_id or owner_id,
                payload.season_id,
                payload.commodity,
                payload.variety,
                str(payload.planting_date),
                str(payload.harvest_date),
                payload.harvest_sequence,
                land_area_ha,
                total_kg,
                marketable_kg,
                damaged_kg,
                payload.land_area,
                payload.land_area_unit,
                payload.harvest_quantity,
                payload.quantity_unit,
                selling_price_kg,
                payload.currency,
                gross_revenue,
                payload.production_cost,
                net_profit,
                payload.sales_channel,
                json.dumps(payload.location.model_dump()) if payload.location else None,
                json.dumps([g.model_dump() for g in payload.quality_grades]) if payload.quality_grades else None,
                json.dumps([c.model_dump() for c in payload.cost_details]) if payload.cost_details else None,
                json.dumps([p.model_dump() for p in payload.pest_disease]) if payload.pest_disease else None,
                payload.damage_cause,
                payload.notes,
                json.dumps(payload.photo_urls) if payload.photo_urls else None,
                initial_status.value,
                payload.source.value,
                json.dumps(kpi_summary.model_dump()),
                now_iso,
                now_iso
            ))
            conn.commit()

        record = self.get_harvest_by_id(harvest_id)
        return record, True

    def list_harvests(
        self,
        user_id: Optional[str] = None,
        farm_id: Optional[str] = None,
        farmer_id: Optional[str] = None,
        commodity: Optional[str] = None,
        status: Optional[HarvestStatusEnum] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[HarvestRecordResponse], int]:
        """Mengambil rekapitulasi data panen terisolasi per akun pengguna."""
        query_conditions = ["status != 'archived'"]
        params = []

        if user_id:
            query_conditions.append("(user_id = ? OR (user_id = 'USR-028' AND NOT EXISTS (SELECT 1 FROM harvests WHERE user_id = ? AND status != 'archived')))")
            params.extend([user_id, user_id])

        if farm_id:
            query_conditions.append("farm_id = ?")
            params.append(farm_id)
        if farmer_id:
            query_conditions.append("farmer_id = ?")
            params.append(farmer_id)
        if commodity:
            query_conditions.append("commodity = ?")
            params.append(commodity)
        if status:
            query_conditions.append("status = ?")
            params.append(status.value)
        if start_date:
            query_conditions.append("harvest_date >= ?")
            params.append(start_date)
        if end_date:
            query_conditions.append("harvest_date <= ?")
            params.append(end_date)

        where_clause = " WHERE " + " AND ".join(query_conditions)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Hitung total
            cursor.execute(f"SELECT COUNT(*) FROM harvests {where_clause}", tuple(params))
            total_count = cursor.fetchone()[0]

            # Ambil item
            cursor.execute(
                f"SELECT * FROM harvests {where_clause} ORDER BY harvest_date DESC, created_at DESC LIMIT ? OFFSET ?",
                tuple(params + [limit, offset])
            )
            rows = cursor.fetchall()
            items = [self._row_to_harvest_response(r) for r in rows]

        return items, total_count

    def update_harvest(
        self,
        harvest_id: str,
        payload: HarvestUpdateRequest,
        user_id: Optional[str] = None
    ) -> Optional[HarvestRecordResponse]:
        record = self.get_harvest_by_id(harvest_id, user_id=user_id)
        if not record:
            return None

        update_fields = []
        params = []

        if payload.selling_price_per_unit is not None:
            selling_price_kg = payload.selling_price_per_unit
            gross_revenue = record.marketable_quantity_kg * selling_price_kg
            net_profit = gross_revenue - record.total_production_cost
            update_fields.extend([
                "selling_price_per_kg = ?",
                "gross_revenue = ?",
                "net_profit = ?"
            ])
            params.extend([selling_price_kg, gross_revenue, net_profit])

        if payload.sales_channel is not None:
            update_fields.append("sales_channel = ?")
            params.append(payload.sales_channel)

        if payload.status is not None:
            update_fields.append("status = ?")
            params.append(payload.status.value)

        if payload.notes is not None:
            update_fields.append("notes = ?")
            params.append(payload.notes)

        if not update_fields:
            return record

        now_iso = datetime.utcnow().isoformat()
        update_fields.append("updated_at = ?")
        params.append(now_iso)
        params.append(harvest_id)

        set_clause = ", ".join(update_fields)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE harvests SET {set_clause} WHERE harvest_id = ?", tuple(params))
            conn.commit()

        # Recompute KPIs if financial fields changed
        updated_record = self.get_harvest_by_id(harvest_id)
        if updated_record and payload.selling_price_per_unit is not None:
            new_kpi = AnalyticsCalculator.calculate_all_kpis(
                harvest_id=updated_record.harvest_id,
                commodity=updated_record.commodity,
                variety=updated_record.variety,
                harvest_date_str=str(updated_record.harvest_date),
                land_area_ha=updated_record.land_area_ha,
                harvest_quantity_kg=updated_record.harvest_quantity_kg,
                marketable_quantity_kg=updated_record.marketable_quantity_kg,
                damaged_quantity_kg=updated_record.damaged_quantity_kg,
                selling_price_per_kg=updated_record.selling_price_per_kg,
                total_production_cost=updated_record.total_production_cost,
                quality_grades=updated_record.quality_grades
            )
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE harvests SET kpi_summary_json = ? WHERE harvest_id = ?",
                    (json.dumps(new_kpi.model_dump()), harvest_id)
                )
                conn.commit()
            updated_record = self.get_harvest_by_id(harvest_id)

        return updated_record

    def delete_harvest(self, harvest_id: str, user_id: Optional[str] = None) -> bool:
        record = self.get_harvest_by_id(harvest_id, user_id=user_id)
        if not record:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            cursor.execute(
                "UPDATE harvests SET status = 'archived', updated_at = ? WHERE harvest_id = ?",
                (now_iso, harvest_id)
            )
            conn.commit()
        return True

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Mengambil data ringkas akun dan statistik panen milik pengguna."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_row = cursor.fetchone()

            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(SUM(harvest_quantity_kg), 0) as total_kg,
                    COALESCE(SUM(gross_revenue), 0) as total_revenue,
                    COALESCE(SUM(net_profit), 0) as total_profit
                FROM harvests
                WHERE user_id = ? AND status != 'archived'
            """, (user_id,))
            stat_row = cursor.fetchone()

            return {
                "user": dict(user_row) if user_row else None,
                "stats": {
                    "total_harvests": stat_row["count"] if stat_row else 0,
                    "total_quantity_kg": stat_row["total_kg"] if stat_row else 0.0,
                    "total_gross_revenue": stat_row["total_revenue"] if stat_row else 0.0,
                    "total_net_profit": stat_row["total_profit"] if stat_row else 0.0,
                }
            }

    # -------------------------------------------------------------
    # Notification & Webhook Configuration Storage
    # -------------------------------------------------------------
    def get_notification_config(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        config_key = f"{user_id}:notification_config" if user_id else "notification_config"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value_json FROM system_config WHERE key = ?", (config_key,))
            row = cursor.fetchone()
            if not row and user_id:
                # fallback ke default general
                cursor.execute("SELECT value_json FROM system_config WHERE key = 'notification_config'")
                row = cursor.fetchone()

            if row:
                return json.loads(row[0])
            return {"webhook_url": "", "is_enabled": True}

    def save_notification_config(self, config: Dict[str, Any], user_id: Optional[str] = None):
        config_key = f"{user_id}:notification_config" if user_id else "notification_config"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO system_config (key, value_json, updated_at) VALUES (?, ?, ?)",
                (config_key, json.dumps(config), now_iso)
            )
            conn.commit()


db_manager = DatabaseManager()
