from typing import Optional, List, Dict
from app.schemas.kpi import ProductionKPIs, EconomicKPIs, HarvestCalculatedKPIs
from app.schemas.harvest import QualityGradeSchema


class AnalyticsCalculator:
    """Implementasi rumus analitik dan KPI panen sesuai Blueprint Bagian 12."""

    @staticmethod
    def calculate_production_kpis(
        land_area_ha: float,
        harvest_quantity_kg: float,
        marketable_quantity_kg: float,
        damaged_quantity_kg: float,
        initial_pop: Optional[int] = None,
        productive_pop: Optional[int] = None
    ) -> ProductionKPIs:
        # Produktivitas (kg/ha) = Total Panen (kg) / Luas Lahan (ha)
        productivity = (harvest_quantity_kg / land_area_ha) if land_area_ha > 0 else 0.0

        # Marketable Yield (%) = (Hasil Layak Jual / Total Panen) * 100
        marketable_yield_pct = (
            (marketable_quantity_kg / harvest_quantity_kg) * 100.0
            if harvest_quantity_kg > 0
            else 0.0
        )

        # Loss Rate (%) = (Hasil Rusak / Total Panen) * 100
        loss_rate_pct = (
            (damaged_quantity_kg / harvest_quantity_kg) * 100.0
            if harvest_quantity_kg > 0
            else 0.0
        )

        # Survival Rate (%) = (Populasi Produktif / Populasi Awal) * 100
        survival_rate_pct = None
        if initial_pop and initial_pop > 0 and productive_pop is not None:
            survival_rate_pct = round((productive_pop / initial_pop) * 100.0, 2)

        return ProductionKPIs(
            productivity_kg_per_ha=round(productivity, 2),
            marketable_yield_percent=round(marketable_yield_pct, 2),
            loss_rate_percent=round(loss_rate_pct, 2),
            survival_rate_percent=survival_rate_pct,
        )

    @staticmethod
    def calculate_economic_kpis(
        marketable_quantity_kg: float,
        harvest_quantity_kg: float,
        selling_price_per_kg: float,
        total_production_cost: float,
        land_area_ha: float,
    ) -> EconomicKPIs:
        # Pendapatan Kotor = Jumlah Terjual (atau layak jual) * Harga Jual per kg
        gross_revenue = marketable_quantity_kg * selling_price_per_kg

        # Keuntungan Bersih = Pendapatan Kotor - Total Biaya
        net_profit = gross_revenue - total_production_cost

        # Biaya per kg = Total Biaya / Total Panen
        cost_per_kg = (
            (total_production_cost / harvest_quantity_kg)
            if harvest_quantity_kg > 0
            else 0.0
        )

        # Margin Keuntungan (%) = (Keuntungan Bersih / Pendapatan Kotor) * 100
        profit_margin_pct = (
            (net_profit / gross_revenue) * 100.0
            if gross_revenue > 0
            else 0.0
        )

        # ROI (%) = (Keuntungan Bersih / Total Biaya) * 100
        roi_pct = (
            (net_profit / total_production_cost) * 100.0
            if total_production_cost > 0
            else 0.0
        )

        # Break-even Price = Total Biaya / Hasil Layak Jual
        break_even_price = (
            (total_production_cost / marketable_quantity_kg)
            if marketable_quantity_kg > 0
            else 0.0
        )

        # Revenue per Hectare = Pendapatan Kotor / Luas Lahan
        rev_per_ha = (gross_revenue / land_area_ha) if land_area_ha > 0 else 0.0

        # Profit per Hectare = Keuntungan Bersih / Luas Lahan
        profit_per_ha = (net_profit / land_area_ha) if land_area_ha > 0 else 0.0

        return EconomicKPIs(
            gross_revenue_idr=round(gross_revenue, 2),
            total_production_cost_idr=round(total_production_cost, 2),
            net_profit_idr=round(net_profit, 2),
            cost_per_kg_idr=round(cost_per_kg, 2),
            profit_margin_percent=round(profit_margin_pct, 2),
            roi_percent=round(roi_pct, 2),
            break_even_price_idr=round(break_even_price, 2),
            revenue_per_ha_idr=round(rev_per_ha, 2),
            profit_per_ha_idr=round(profit_per_ha, 2),
        )

    @classmethod
    def calculate_all_kpis(
        cls,
        harvest_id: str,
        commodity: str,
        variety: Optional[str],
        harvest_date_str: str,
        land_area_ha: float,
        harvest_quantity_kg: float,
        marketable_quantity_kg: float,
        damaged_quantity_kg: float,
        selling_price_per_kg: float,
        total_production_cost: float,
        quality_grades: Optional[List[QualityGradeSchema]] = None,
        initial_pop: Optional[int] = None,
        productive_pop: Optional[int] = None
    ) -> HarvestCalculatedKPIs:
        
        prod_kpi = cls.calculate_production_kpis(
            land_area_ha=land_area_ha,
            harvest_quantity_kg=harvest_quantity_kg,
            marketable_quantity_kg=marketable_quantity_kg,
            damaged_quantity_kg=damaged_quantity_kg,
            initial_pop=initial_pop,
            productive_pop=productive_pop
        )

        econ_kpi = cls.calculate_economic_kpis(
            marketable_quantity_kg=marketable_quantity_kg,
            harvest_quantity_kg=harvest_quantity_kg,
            selling_price_per_kg=selling_price_per_kg,
            total_production_cost=total_production_cost,
            land_area_ha=land_area_ha
        )

        # Distribusi Grade Mutu
        quality_dist: Dict[str, float] = {}
        if quality_grades and harvest_quantity_kg > 0:
            for g in quality_grades:
                pct = round((g.quantity_kg / harvest_quantity_kg) * 100.0, 2)
                quality_dist[f"Grade {g.grade}"] = pct

        return HarvestCalculatedKPIs(
            harvest_id=harvest_id,
            commodity=commodity,
            variety=variety,
            harvest_date=harvest_date_str,
            land_area_ha=land_area_ha,
            total_harvest_kg=harvest_quantity_kg,
            marketable_kg=marketable_quantity_kg,
            damaged_kg=damaged_quantity_kg,
            production_kpis=prod_kpi,
            economic_kpis=econ_kpi,
            quality_distribution_percent=quality_dist
        )
