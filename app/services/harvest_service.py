from typing import Dict, List, Optional, Tuple

from app.schemas.common import HarvestStatusEnum, DataSourceEnum
from app.schemas.harvest import (
    HarvestCreateRequest,
    HarvestUpdateRequest,
    HarvestRecordResponse,
)
from app.services.db import db_manager


class HarvestService:
    """Service manajemen data hasil panen yang terhubung ke Database Relasional Persisten."""

    def create_harvest(
        self,
        payload: HarvestCreateRequest,
        custom_id: Optional[str] = None,
        initial_status: HarvestStatusEnum = HarvestStatusEnum.VALIDATED
    ) -> Tuple[HarvestRecordResponse, bool]:
        """Menyimpan data panen baru ke database dengan ACID transaction & idempotency."""
        return db_manager.insert_harvest(
            payload=payload,
            custom_id=custom_id,
            initial_status=initial_status
        )

    def get_harvest(self, harvest_id: str) -> Optional[HarvestRecordResponse]:
        """Mengambil detail record panen spesifik dari database."""
        return db_manager.get_harvest_by_id(harvest_id)

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
        """Query data panen dengan filter terindeks dari database."""
        return db_manager.list_harvests(
            farm_id=farm_id,
            farmer_id=farmer_id,
            commodity=commodity,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

    def update_harvest(
        self,
        harvest_id: str,
        update_payload: HarvestUpdateRequest
    ) -> Optional[HarvestRecordResponse]:
        """Memperbarui data atau status panen di database."""
        return db_manager.update_harvest(harvest_id, update_payload)

    def delete_harvest(self, harvest_id: str) -> bool:
        """Soft delete (mengarsipkan) data panen di database."""
        return db_manager.delete_harvest(harvest_id)


# Singleton instance
harvest_service = HarvestService()
