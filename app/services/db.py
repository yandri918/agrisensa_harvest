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
    """Manajer Database Relasional Persisten (Real SQLite Database Engine dengan ACID Compliance)."""

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
        """Membuat tabel skema database relasional jika belum ada."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tabel Utama Rekapitulasi Panen
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS harvests (
                    harvest_id TEXT PRIMARY KEY,
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

            # 2. Indeks untuk Query & Filter Berkinerja Tinggi
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_commodity ON harvests(commodity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_farm_id ON harvests(farm_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_harvest_date ON harvests(harvest_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_status ON harvests(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_harvests_idempotency ON harvests(idempotency_key)")

            # 3. Tabel Konfigurasi Sistem & Webhook
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.commit()

    def _ensure_seed_data(self):
        """Memastikan data awal terisi jika database masih kosong."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM harvests WHERE status != 'archived'")
            count = cursor.fetchone()[0]
            
            if count == 0:
                sample_id = "h0000000-0000-0000-0000-000000000001"
                sample_req = HarvestCreateRequest(
                    idempotency_key="IDEMP-20260917-CABAI-001",
                    farm_id="FARM-001",
                    farmer_id="USR-028",
                    season_id="SEASON-2026-01",
                    commodity="Cabai Merah",
                    variety="Lado F1",
                    planting_date="2026-05-10",
                    harvest_date="2026-09-17",
                    harvest_sequence=3,
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
                    notes="Panen ketiga dengan mutu dominan grade A",
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
                self.insert_harvest(sample_req, custom_id=sample_id, initial_status=HarvestStatusEnum.APPROVED)

    def _row_to_harvest_response(self, row: sqlite3.Row) -> HarvestRecordResponse:
        """Mengonversi row SQLite ke objek Pydantic HarvestRecordResponse."""
        kpi_dict = json.loads(row["kpi_summary_json"]) if row["kpi_summary_json"] else None
        kpi_obj = HarvestCalculatedKPIs(**kpi_dict) if kpi_dict else None

        return HarvestRecordResponse(
            harvest_id=row["harvest_id"],
            idempotency_key=row["idempotency_key"],
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

    def get_harvest_by_id(self, harvest_id: str) -> Optional[HarvestRecordResponse]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM harvests WHERE harvest_id = ?", (harvest_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_harvest_response(row)

    def get_harvest_by_idempotency(self, key: str) -> Optional[HarvestRecordResponse]:
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
        initial_status: HarvestStatusEnum = HarvestStatusEnum.VALIDATED
    ) -> Tuple[HarvestRecordResponse, bool]:
        # Cek Idempotency Key
        if payload.idempotency_key:
            existing = self.get_harvest_by_idempotency(payload.idempotency_key)
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
                    harvest_id, idempotency_key, farm_id, farmer_id, season_id, commodity, variety,
                    planting_date, harvest_date, harvest_sequence, land_area_ha, harvest_quantity_kg,
                    marketable_quantity_kg, damaged_quantity_kg, original_land_area, original_land_area_unit,
                    original_quantity, original_quantity_unit, selling_price_per_kg, currency, gross_revenue,
                    total_production_cost, net_profit, sales_channel, location_json, quality_grades_json,
                    cost_details_json, pest_disease_json, damage_cause, notes, photo_urls_json,
                    status, source, kpi_summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                harvest_id,
                payload.idempotency_key,
                payload.farm_id,
                payload.farmer_id,
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
        farm_id: Optional[str] = None,
        farmer_id: Optional[str] = None,
        commodity: Optional[str] = None,
        status: Optional[HarvestStatusEnum] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[HarvestRecordResponse], int]:
        query_conditions = ["status != 'archived'"]
        params = []

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

    def update_harvest(self, harvest_id: str, payload: HarvestUpdateRequest) -> Optional[HarvestRecordResponse]:
        record = self.get_harvest_by_id(harvest_id)
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

    def delete_harvest(self, harvest_id: str) -> bool:
        record = self.get_harvest_by_id(harvest_id)
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

    # -------------------------------------------------------------
    # Notification & Webhook Configuration Storage
    # -------------------------------------------------------------
    def get_notification_config(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value_json FROM system_config WHERE key = 'notification_config'")
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return {"webhook_url": "", "is_enabled": True}

    def save_notification_config(self, config: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO system_config (key, value_json, updated_at) VALUES (?, ?, ?)",
                ("notification_config", json.dumps(config), now_iso)
            )
            conn.commit()


db_manager = DatabaseManager()
