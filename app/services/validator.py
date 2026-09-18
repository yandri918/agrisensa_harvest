from typing import List, Optional
from app.schemas.harvest import HarvestCreateRequest


class HarvestValidator:
    """Validasi integritas bisnis record panen sesuai Blueprint Bagian 8.2."""

    @staticmethod
    def validate_create_payload(payload: HarvestCreateRequest) -> List[str]:
        errors: List[str] = []

        # 1. Validasi Tanggal
        if payload.harvest_date < payload.planting_date:
            errors.append(
                f"Tanggal panen ({payload.harvest_date}) tidak boleh lebih awal dari tanggal tanam ({payload.planting_date})."
            )

        # 2. Validasi Luas & Kuantitas
        if payload.land_area <= 0:
            errors.append("Luas lahan (land_area) harus lebih besar dari 0.")

        if payload.harvest_quantity <= 0:
            errors.append("Kuantitas panen (harvest_quantity) harus lebih besar dari 0.")

        # 3. Validasi Konsistensi Layak Jual & Rusak
        marketable = (
            payload.marketable_quantity
            if payload.marketable_quantity is not None
            else (payload.harvest_quantity - (payload.damaged_quantity or 0.0))
        )
        damaged = payload.damaged_quantity or 0.0

        if marketable < 0:
            errors.append("Kuantitas layak jual (marketable_quantity) tidak boleh bernilai negatif.")

        if (marketable + damaged) > (payload.harvest_quantity + 0.01):
            errors.append(
                f"Total hasil layak ({marketable}) + rusak ({damaged}) melebihi total panen ({payload.harvest_quantity})."
            )

        # 4. Validasi Keuangan
        if payload.selling_price_per_unit and payload.selling_price_per_unit < 0:
            errors.append("Harga jual per unit tidak boleh negatif.")

        if payload.production_cost and payload.production_cost < 0:
            errors.append("Biaya produksi tidak boleh negatif.")

        # 5. Validasi Koordinat Lokasi jika diberikan
        if payload.location:
            if payload.location.latitude is not None and not (-90 <= payload.location.latitude <= 90):
                errors.append("Latitude harus berada di antara -90 dan 90 derajat.")
            if payload.location.longitude is not None and not (-180 <= payload.location.longitude <= 180):
                errors.append("Longitude harus berada di antara -180 dan 180 derajat.")

        return errors
