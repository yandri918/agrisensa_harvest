from typing import Optional, Dict
from pydantic import BaseModel, Field


class ProductionKPIs(BaseModel):
    productivity_kg_per_ha: float = Field(..., description="Produktivitas dalam kg/ha (Total Panen / Luas Lahan)")
    marketable_yield_percent: float = Field(..., description="Persentase hasil layak jual (%)")
    loss_rate_percent: float = Field(..., description="Persentase kehilangan / kerusakan hasil (%)")
    survival_rate_percent: Optional[float] = Field(None, description="Tingkat populasi produktif (%)")


class EconomicKPIs(BaseModel):
    gross_revenue_idr: float = Field(..., description="Total pendapatan kotor (IDR)")
    total_production_cost_idr: float = Field(..., description="Total biaya produksi (IDR)")
    net_profit_idr: float = Field(..., description="Keuntungan bersih (IDR)")
    cost_per_kg_idr: float = Field(..., description="Biaya produksi per kg (IDR/kg)")
    profit_margin_percent: float = Field(..., description="Margin keuntungan (%)")
    roi_percent: float = Field(..., description="Return on Investment (%)")
    break_even_price_idr: float = Field(..., description="Harga impas per kg (BEP)")
    revenue_per_ha_idr: float = Field(..., description="Pendapatan per hektar (IDR/ha)")
    profit_per_ha_idr: float = Field(..., description="Keuntungan per hektar (IDR/ha)")


class HarvestCalculatedKPIs(BaseModel):
    harvest_id: str
    commodity: str
    variety: Optional[str] = None
    harvest_date: str
    land_area_ha: float
    total_harvest_kg: float
    marketable_kg: float
    damaged_kg: float
    production_kpis: ProductionKPIs
    economic_kpis: EconomicKPIs
    quality_distribution_percent: Dict[str, float] = Field(default_factory=dict)
