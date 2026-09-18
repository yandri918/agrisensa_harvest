from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.common import ApiResponse
from app.schemas.kpi import HarvestCalculatedKPIs
from app.services.harvest_service import harvest_service

router = APIRouter(prefix="/analytics", tags=["Analytics & KPIs"])


@router.get(
    "/kpis/{harvest_id}",
    response_model=ApiResponse[HarvestCalculatedKPIs],
    summary="Mengambil kalkulasi KPI lengkap dari suatu panen",
)
def get_harvest_kpis(harvest_id: str):
    record = harvest_service.get_harvest(harvest_id)
    if not record or not record.kpi_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KPI untuk panen ID '{harvest_id}' tidak ditemukan."
        )
    return ApiResponse(
        success=True,
        message="Kalkulasi KPI berhasil diambil.",
        data=record.kpi_summary
    )


@router.get(
    "/summary",
    response_model=ApiResponse[dict],
    summary="Mengambil ringkasan agregat analitik (total panen, rata-rata produktivitas, total pendapatan)",
)
def get_analytics_summary(
    commodity: Optional[str] = Query(None, description="Filter komoditas"),
    farm_id: Optional[str] = Query(None, description="Filter kebun"),
    start_date: Optional[str] = Query(None, description="Tanggal panen awal"),
    end_date: Optional[str] = Query(None, description="Tanggal panen akhir"),
):
    records, total_count = harvest_service.list_harvests(
        commodity=commodity,
        farm_id=farm_id,
        start_date=start_date,
        end_date=end_date,
        limit=1000
    )

    if not records:
        return ApiResponse(
            success=True,
            message="Belum ada data panen yang sesuai filter.",
            data={
                "total_records": 0,
                "total_harvest_kg": 0,
                "total_gross_revenue_idr": 0,
                "total_net_profit_idr": 0,
                "avg_productivity_kg_per_ha": 0,
                "avg_marketable_yield_percent": 0,
                "avg_roi_percent": 0,
            }
        )

    total_harvest_kg = sum(r.harvest_quantity_kg for r in records)
    total_revenue = sum(r.gross_revenue for r in records)
    total_profit = sum(r.net_profit for r in records)
    total_area_ha = sum(r.land_area_ha for r in records)

    avg_productivity = (total_harvest_kg / total_area_ha) if total_area_ha > 0 else 0
    
    # Rata-rata dari KPI summary
    valid_kpis = [r.kpi_summary for r in records if r.kpi_summary]
    avg_marketable_pct = (
        sum(k.production_kpis.marketable_yield_percent for k in valid_kpis) / len(valid_kpis)
        if valid_kpis
        else 0
    )
    avg_roi_pct = (
        sum(k.economic_kpis.roi_percent for k in valid_kpis) / len(valid_kpis)
        if valid_kpis
        else 0
    )

    summary_data = {
        "total_records": len(records),
        "total_harvest_kg": round(total_harvest_kg, 2),
        "total_gross_revenue_idr": round(total_revenue, 2),
        "total_net_profit_idr": round(total_profit, 2),
        "total_land_area_ha": round(total_area_ha, 4),
        "avg_productivity_kg_per_ha": round(avg_productivity, 2),
        "avg_marketable_yield_percent": round(avg_marketable_pct, 2),
        "avg_roi_percent": round(avg_roi_pct, 2),
    }

    return ApiResponse(
        success=True,
        message="Ringkasan agregasi analitik panen berhasil dihitung.",
        data=summary_data
    )


from app.services.ai_insight_service import ai_insight_service


@router.get(
    "/ai-insights/{harvest_id}",
    response_model=ApiResponse[dict],
    summary="Mengambil evaluasi benchmark AI dan rekomendasi agronomi untuk record panen tertentu",
)
def get_harvest_ai_insights(harvest_id: str):
    record = harvest_service.get_harvest(harvest_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    insights = ai_insight_service.evaluate_harvest_record(record)
    return ApiResponse(
        success=True,
        message="Evaluasi AI dan rekomendasi agronomi berhasil dihitung.",
        data=insights
    )


@router.get(
    "/ai-insights",
    response_model=ApiResponse[dict],
    summary="Mengambil ringkasan evaluasi benchmark AI agregat berdasarkan filter aktif",
)
def get_summary_ai_insights(
    commodity: Optional[str] = Query(None, description="Filter komoditas"),
    farm_id: Optional[str] = Query(None, description="Filter kebun"),
    start_date: Optional[str] = Query(None, description="Tanggal panen awal"),
    end_date: Optional[str] = Query(None, description="Tanggal panen akhir"),
):
    records, _ = harvest_service.list_harvests(
        commodity=commodity,
        farm_id=farm_id,
        start_date=start_date,
        end_date=end_date,
        limit=1000
    )

    if not records:
        return ApiResponse(
            success=True,
            message="Belum ada data untuk evaluasi AI.",
            data={"insights": ["Belum ada data panen yang tercatat."]}
        )

    # Calculate summary
    total_kg = sum(r.harvest_quantity_kg for r in records)
    total_area = sum(r.land_area_ha for r in records)
    avg_prod = (total_kg / total_area) if total_area > 0 else 0

    valid_kpis = [r.kpi_summary for r in records if r.kpi_summary]
    avg_marketable = (
        sum(k.production_kpis.marketable_yield_percent for k in valid_kpis) / len(valid_kpis)
        if valid_kpis else 0
    )
    avg_roi = (
        sum(k.economic_kpis.roi_percent for k in valid_kpis) / len(valid_kpis)
        if valid_kpis else 0
    )

    summary_dict = {
        "avg_productivity_kg_per_ha": avg_prod,
        "avg_marketable_yield_percent": avg_marketable,
        "avg_roi_percent": avg_roi
    }

    insights_data = ai_insight_service.evaluate_summary_data(summary_dict, commodity)
    return ApiResponse(
        success=True,
        message="Evaluasi AI agregat berhasil dihitung.",
        data=insights_data
    )

