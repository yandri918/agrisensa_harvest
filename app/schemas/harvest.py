from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
from app.schemas.common import HarvestStatusEnum, DataSourceEnum
from app.schemas.kpi import HarvestCalculatedKPIs


class LocationSchema(BaseModel):
    village: Optional[str] = Field(None, description="Nama desa / kelurahan")
    district: Optional[str] = Field(None, description="Nama kecamatan")
    regency: Optional[str] = Field(None, description="Nama kabupaten / kota")
    province: Optional[str] = Field(None, description="Nama provinsi")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    altitude_masl: Optional[float] = None


class QualityGradeSchema(BaseModel):
    grade: str = Field(..., description="Nama grade, contoh: 'A', 'B', 'C'")
    quantity_kg: float = Field(..., ge=0, description="Kuantitas grade dalam kg")
    price_per_kg: Optional[float] = Field(0.0, ge=0)
    notes: Optional[str] = None


class ProductionCostItemSchema(BaseModel):
    category: str = Field(..., description="bibit, pupuk, pestisida, tenaga_kerja, irigasi, sewa_lahan, kemasan, transportasi, lainnya")
    description: Optional[str] = None
    amount: float = Field(..., ge=0, description="Jumlah biaya")
    currency: str = "IDR"


class PestDiseaseSchema(BaseModel):
    name: str = Field(..., description="Nama hama / penyakit")
    severity_percent: Optional[float] = Field(None, ge=0, le=100)
    treatment: Optional[str] = None


class HarvestCreateRequest(BaseModel):
    idempotency_key: Optional[str] = Field(None, description="Kunci pencegah duplikasi request")
    farm_id: str = Field(..., description="ID / kode kebun")
    farmer_id: str = Field(..., description="ID / kode petani")
    season_id: Optional[str] = Field(None, description="ID musim tanam")
    plot_id: Optional[str] = None
    
    commodity: str = Field(..., description="Nama komoditas, contoh: 'Cabai Merah'")
    variety: Optional[str] = Field(None, description="Varietas tanaman, contoh: 'Lado F1'")
    
    planting_date: date = Field(..., description="Tanggal tanam (YYYY-MM-DD)")
    harvest_date: date = Field(..., description="Tanggal panen (YYYY-MM-DD)")
    harvest_sequence: int = Field(1, ge=1, description="Panen ke-n")
    
    land_area: float = Field(..., gt=0, description="Luas lahan")
    land_area_unit: str = Field("ha", description="Satuan luas: 'ha', 'm2', 'bata', 'ru', 'hektare'")
    
    initial_plant_population: Optional[int] = Field(None, ge=0)
    productive_plant_population: Optional[int] = Field(None, ge=0)
    
    harvest_quantity: float = Field(..., ge=0, description="Total kuantitas hasil panen")
    quantity_unit: str = Field("kg", description="Satuan panen: 'kg', 'ton', 'kuintal', 'peti', 'ikat'")
    
    marketable_quantity: Optional[float] = Field(None, ge=0, description="Hasil layak jual")
    damaged_quantity: Optional[float] = Field(0.0, ge=0, description="Hasil rusak / afkir")
    
    selling_price_per_unit: Optional[float] = Field(0.0, ge=0, description="Harga jual per unit")
    currency: str = Field("IDR", max_length=5)
    
    production_cost: Optional[float] = Field(0.0, ge=0, description="Total biaya produksi")
    sales_channel: Optional[str] = Field(None, description="pasar_induk, supermarket, tengkulak, langsung, dll")
    
    location: Optional[LocationSchema] = None
    quality_grades: Optional[List[QualityGradeSchema]] = Field(default_factory=list)
    cost_details: Optional[List[ProductionCostItemSchema]] = Field(default_factory=list)
    pest_disease: Optional[List[PestDiseaseSchema]] = Field(default_factory=list)
    
    damage_cause: Optional[str] = None
    notes: Optional[str] = None
    photo_urls: Optional[List[str]] = Field(default_factory=list)
    source: DataSourceEnum = DataSourceEnum.API

    @field_validator("harvest_date")
    def validate_harvest_after_planting(cls, v, info):
        if "planting_date" in info.data and v < info.data["planting_date"]:
            raise ValueError("Tanggal panen (harvest_date) tidak boleh lebih awal dari tanggal tanam (planting_date)")
        return v


class HarvestUpdateRequest(BaseModel):
    harvest_sequence: Optional[int] = Field(None, ge=1)
    harvest_quantity: Optional[float] = Field(None, ge=0)
    marketable_quantity: Optional[float] = Field(None, ge=0)
    damaged_quantity: Optional[float] = Field(None, ge=0)
    selling_price_per_unit: Optional[float] = Field(None, ge=0)
    production_cost: Optional[float] = Field(None, ge=0)
    sales_channel: Optional[str] = None
    damage_cause: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[HarvestStatusEnum] = None


class HarvestRecordResponse(BaseModel):
    harvest_id: str
    idempotency_key: Optional[str] = None
    farm_id: str
    farmer_id: str
    season_id: Optional[str] = None
    commodity: str
    variety: Optional[str] = None
    
    planting_date: date
    harvest_date: date
    harvest_sequence: int
    
    # Normalized Standard Units
    land_area_ha: float
    harvest_quantity_kg: float
    marketable_quantity_kg: float
    damaged_quantity_kg: float
    
    # Original Input Units
    original_land_area: float
    original_land_area_unit: str
    original_quantity: float
    original_quantity_unit: str
    
    # Financials
    selling_price_per_kg: float
    currency: str
    gross_revenue: float
    total_production_cost: float
    net_profit: float
    sales_channel: Optional[str] = None
    
    # Nested Details
    location: Optional[LocationSchema] = None
    quality_grades: List[QualityGradeSchema] = Field(default_factory=list)
    cost_details: List[ProductionCostItemSchema] = Field(default_factory=list)
    pest_disease: List[PestDiseaseSchema] = Field(default_factory=list)
    
    damage_cause: Optional[str] = None
    notes: Optional[str] = None
    photo_urls: List[str] = Field(default_factory=list)
    
    status: HarvestStatusEnum
    source: DataSourceEnum
    
    # Computed KPI Summary
    kpi_summary: Optional[HarvestCalculatedKPIs] = None
    
    created_at: datetime
    updated_at: datetime
