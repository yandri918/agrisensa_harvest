import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.schemas.common import HarvestStatusEnum, DataSourceEnum
from app.schemas.harvest import (
    HarvestCreateRequest,
    HarvestUpdateRequest,
    HarvestRecordResponse,
)
from app.services.normalizer import UnitNormalizer
from app.services.validator import HarvestValidator
from app.services.analytics_service import AnalyticsCalculator


class HarvestService:
    """Service manajemen data hasil panen dengan in-memory storage + database sync readiness."""

    def __init__(self):
        # Menyimpan record panen: harvest_id -> HarvestRecordResponse
        self._records: Dict[str, HarvestRecordResponse] = {}
        # Memetakan idempotency_key -> harvest_id
        self._idempotency_map: Dict[str, str] = {}
        # Riwayat sinkronisasi & event log
        self._events: List[Dict] = []
        
        # Inisialisasi seed sample awal
        self._init_seed_data()

    def _init_seed_data(self):
        """Memasukkan record panen contoh sesuai Blueprint Bagian 7."""
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
        self.create_harvest(sample_req, custom_id=sample_id, initial_status=HarvestStatusEnum.APPROVED)

    def create_harvest(
        self,
        payload: HarvestCreateRequest,
        custom_id: Optional[str] = None,
        initial_status: HarvestStatusEnum = HarvestStatusEnum.VALIDATED
    ) -> Tuple[HarvestRecordResponse, bool]:
        """
        Membuat data panen baru.
        Mendukung idempotency: jika idempotency_key sudah ada, mengembalikan record yang sudah ada (is_new = False).
        """
        # 1. Cek Idempotency Key
        if payload.idempotency_key and payload.idempotency_key in self._idempotency_map:
            existing_id = self._idempotency_map[payload.idempotency_key]
            return self._records[existing_id], False

        # 2. Validasi Logika Bisnis
        validation_errors = HarvestValidator.validate_create_payload(payload)
        if validation_errors:
            raise ValueError(" | ".join(validation_errors))

        # 3. Normalisasi Unit ke Satuan Standar (kg & ha)
        norm_land_area_ha = UnitNormalizer.normalize_area_to_ha(
            payload.land_area, payload.land_area_unit
        )
        norm_harvest_kg = UnitNormalizer.normalize_weight_to_kg(
            payload.harvest_quantity, payload.quantity_unit
        )
        
        raw_marketable = (
            payload.marketable_quantity
            if payload.marketable_quantity is not None
            else (payload.harvest_quantity - (payload.damaged_quantity or 0.0))
        )
        norm_marketable_kg = UnitNormalizer.normalize_weight_to_kg(
            raw_marketable, payload.quantity_unit
        )
        norm_damaged_kg = UnitNormalizer.normalize_weight_to_kg(
            payload.damaged_quantity or 0.0, payload.quantity_unit
        )
        
        selling_price_kg = UnitNormalizer.normalize_price_per_kg(
            payload.selling_price_per_unit or 0.0, payload.quantity_unit
        )

        # 4. Perhitungan Keuangan
        gross_revenue = round(norm_marketable_kg * selling_price_kg, 2)
        total_cost = round(payload.production_cost or 0.0, 2)
        net_profit = round(gross_revenue - total_cost, 2)

        harvest_id = custom_id or str(uuid.uuid4())
        now = datetime.utcnow()

        # 5. Hitung KPI Otomatis
        kpi_summary = AnalyticsCalculator.calculate_all_kpis(
            harvest_id=harvest_id,
            commodity=payload.commodity,
            variety=payload.variety,
            harvest_date_str=str(payload.harvest_date),
            land_area_ha=norm_land_area_ha,
            harvest_quantity_kg=norm_harvest_kg,
            marketable_quantity_kg=norm_marketable_kg,
            damaged_quantity_kg=norm_damaged_kg,
            selling_price_per_kg=selling_price_kg,
            total_production_cost=total_cost,
            quality_grades=payload.quality_grades,
            initial_pop=payload.initial_plant_population,
            productive_pop=payload.productive_plant_population,
        )

        # 6. Bentuk Objek Record Response
        record = HarvestRecordResponse(
            harvest_id=harvest_id,
            idempotency_key=payload.idempotency_key,
            farm_id=payload.farm_id,
            farmer_id=payload.farmer_id,
            season_id=payload.season_id,
            commodity=payload.commodity.strip(),
            variety=payload.variety.strip() if payload.variety else None,
            planting_date=payload.planting_date,
            harvest_date=payload.harvest_date,
            harvest_sequence=payload.harvest_sequence,
            land_area_ha=norm_land_area_ha,
            harvest_quantity_kg=norm_harvest_kg,
            marketable_quantity_kg=norm_marketable_kg,
            damaged_quantity_kg=norm_damaged_kg,
            original_land_area=payload.land_area,
            original_land_area_unit=payload.land_area_unit,
            original_quantity=payload.harvest_quantity,
            original_quantity_unit=payload.quantity_unit,
            selling_price_per_kg=selling_price_kg,
            currency=payload.currency.upper(),
            gross_revenue=gross_revenue,
            total_production_cost=total_cost,
            net_profit=net_profit,
            sales_channel=payload.sales_channel,
            location=payload.location,
            quality_grades=payload.quality_grades or [],
            cost_details=payload.cost_details or [],
            pest_disease=payload.pest_disease or [],
            damage_cause=payload.damage_cause,
            notes=payload.notes,
            photo_urls=payload.photo_urls or [],
            status=initial_status,
            source=payload.source,
            kpi_summary=kpi_summary,
            created_at=now,
            updated_at=now,
        )

        self._records[harvest_id] = record
        if payload.idempotency_key:
            self._idempotency_map[payload.idempotency_key] = harvest_id

        # Menerbitkan Event
        self._events.append({
            "event_type": "harvest.created",
            "harvest_id": harvest_id,
            "timestamp": now.isoformat(),
            "status": str(initial_status)
        })

        return record, True

    def get_harvest(self, harvest_id: str) -> Optional[HarvestRecordResponse]:
        return self._records.get(harvest_id)

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
        """Query & filter harvest records."""
        results = list(self._records.values())

        if farm_id:
            results = [r for r in results if r.farm_id == farm_id]
        if farmer_id:
            results = [r for r in results if r.farmer_id == farmer_id]
        if commodity:
            results = [r for r in results if r.commodity.lower() == commodity.lower()]
        if status:
            results = [r for r in results if r.status == status]
        if start_date:
            results = [r for r in results if str(r.harvest_date) >= start_date]
        if end_date:
            results = [r for r in results if str(r.harvest_date) <= end_date]

        # Urutkan berdasarkan tanggal panen terbaru
        results.sort(key=lambda x: x.harvest_date, reverse=True)
        total = len(results)
        paginated = results[offset : offset + limit]
        return paginated, total

    def update_harvest(
        self, harvest_id: str, update_payload: HarvestUpdateRequest
    ) -> Optional[HarvestRecordResponse]:
        record = self._records.get(harvest_id)
        if not record:
            return None

        # Update field jika diberikan
        data = record.model_dump()
        if update_payload.harvest_sequence is not None:
            data["harvest_sequence"] = update_payload.harvest_sequence
        if update_payload.harvest_quantity is not None:
            data["harvest_quantity_kg"] = update_payload.harvest_quantity
        if update_payload.marketable_quantity is not None:
            data["marketable_quantity_kg"] = update_payload.marketable_quantity
        if update_payload.damaged_quantity is not None:
            data["damaged_quantity_kg"] = update_payload.damaged_quantity
        if update_payload.selling_price_per_unit is not None:
            data["selling_price_per_kg"] = update_payload.selling_price_per_unit
        if update_payload.production_cost is not None:
            data["total_production_cost"] = update_payload.production_cost
        if update_payload.sales_channel is not None:
            data["sales_channel"] = update_payload.sales_channel
        if update_payload.damage_cause is not None:
            data["damage_cause"] = update_payload.damage_cause
        if update_payload.notes is not None:
            data["notes"] = update_payload.notes
        if update_payload.status is not None:
            data["status"] = update_payload.status

        # Recalculate keuangan & KPI
        data["gross_revenue"] = round(data["marketable_quantity_kg"] * data["selling_price_per_kg"], 2)
        data["net_profit"] = round(data["gross_revenue"] - data["total_production_cost"], 2)
        data["updated_at"] = datetime.utcnow()

        # Recalculate KPIs
        kpi_summary = AnalyticsCalculator.calculate_all_kpis(
            harvest_id=harvest_id,
            commodity=data["commodity"],
            variety=data.get("variety"),
            harvest_date_str=str(data["harvest_date"]),
            land_area_ha=data["land_area_ha"],
            harvest_quantity_kg=data["harvest_quantity_kg"],
            marketable_quantity_kg=data["marketable_quantity_kg"],
            damaged_quantity_kg=data["damaged_quantity_kg"],
            selling_price_per_kg=data["selling_price_per_kg"],
            total_production_cost=data["total_production_cost"],
            quality_grades=record.quality_grades
        )
        data["kpi_summary"] = kpi_summary

        updated_record = HarvestRecordResponse(**data)
        self._records[harvest_id] = updated_record
        return updated_record

    def delete_harvest(self, harvest_id: str) -> bool:
        """Soft delete dengan mengubah status menjadi archived."""
        record = self._records.get(harvest_id)
        if not record:
            return False
        record.status = HarvestStatusEnum.ARCHIVED
        record.updated_at = datetime.utcnow()
        return True


# Singleton instance
harvest_service = HarvestService()
