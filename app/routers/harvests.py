import csv
import io
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import Response, HTMLResponse

from app.schemas.common import ApiResponse, PaginatedResponse, HarvestStatusEnum
from app.schemas.harvest import (
    HarvestCreateRequest,
    HarvestUpdateRequest,
    HarvestRecordResponse,
)
from app.services.harvest_service import harvest_service
from app.services.report_service import report_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/harvests", tags=["Harvest Ingest & Management"])


@router.post(
    "",
    response_model=ApiResponse[HarvestRecordResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat data hasil panen baru (Data Ingest)",
    description="Menerima, memvalidasi, menormalisasi unit, menghitung KPI otomatis, dan menyimpan data hasil panen."
)
def create_harvest_record(payload: HarvestCreateRequest, background_tasks: BackgroundTasks):
    try:
        record, is_new = harvest_service.create_harvest(payload)
        
        # Trigger background webhook / WhatsApp notification if new record
        if is_new:
            background_tasks.add_task(notification_service.send_harvest_notification, record)

        msg = "Data panen berhasil disimpan dan tervalidasi." if is_new else "Data panen (idempotent duplicate) ditemukan."
        return ApiResponse(
            success=True,
            message=msg,
            data=record
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


@router.get(
    "/export/csv",
    summary="Mengekspor seluruh rekapitulasi data panen ke format CSV / Excel",
)
def export_harvests_csv(
    farm_id: Optional[str] = Query(None, description="Filter berdasarkan ID kebun"),
    farmer_id: Optional[str] = Query(None, description="Filter berdasarkan ID petani"),
    commodity: Optional[str] = Query(None, description="Filter nama komoditas"),
    status: Optional[HarvestStatusEnum] = Query(None, description="Filter status validasi"),
    start_date: Optional[str] = Query(None, description="Tanggal panen mulai (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Tanggal panen akhir (YYYY-MM-DD)"),
):
    items, _ = harvest_service.list_harvests(
        farm_id=farm_id,
        farmer_id=farmer_id,
        commodity=commodity,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)

    # Header kolom Excel / CSV
    writer.writerow([
        "ID Panen",
        "Komoditas",
        "Varietas",
        "ID Kebun",
        "ID Petani",
        "Tanggal Tanam",
        "Tanggal Panen",
        "Panen Ke",
        "Luas Lahan (ha)",
        "Total Panen (kg)",
        "Layak Jual (kg)",
        "Rusak / Afkir (kg)",
        "Loss Rate (%)",
        "Harga Jual (Rp/kg)",
        "Omset Kotor (Rp)",
        "Biaya Produksi (Rp)",
        "Laba Bersih (Rp)",
        "Produktivitas (kg/ha)",
        "ROI (%)",
        "BEP (Rp/kg)",
        "Kanal Penjualan",
        "Status"
    ])

    for r in items:
        kpi = r.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None

        writer.writerow([
            r.harvest_id,
            r.commodity,
            r.variety or "-",
            r.farm_id,
            r.farmer_id,
            str(r.planting_date),
            str(r.harvest_date),
            r.harvest_sequence,
            r.land_area_ha,
            r.harvest_quantity_kg,
            r.marketable_quantity_kg,
            r.damaged_quantity_kg,
            f"{prod_kpi.loss_rate_percent:.2f}" if prod_kpi else "0",
            r.selling_price_per_kg,
            r.gross_revenue,
            r.total_production_cost,
            r.net_profit,
            f"{prod_kpi.productivity_kg_per_ha:.1f}" if prod_kpi else "0",
            f"{econ_kpi.roi_percent:.2f}" if econ_kpi else "0",
            f"{econ_kpi.break_even_price_idr:.2f}" if econ_kpi else "0",
            r.sales_channel or "-",
            r.status
        ])

    csv_content = output.getvalue()
    filename = f"AgriSensa_Rekap_Panen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[HarvestRecordResponse]],
    summary="Mencari dan memfilter daftar hasil panen",
)
def list_harvest_records(
    farm_id: Optional[str] = Query(None, description="Filter berdasarkan ID kebun"),
    farmer_id: Optional[str] = Query(None, description="Filter berdasarkan ID petani"),
    commodity: Optional[str] = Query(None, description="Filter nama komoditas"),
    status: Optional[HarvestStatusEnum] = Query(None, description="Filter status validasi"),
    start_date: Optional[str] = Query(None, description="Tanggal panen mulai (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Tanggal panen akhir (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Nomor halaman"),
    page_size: int = Query(20, ge=1, le=100, description="Jumlah data per halaman"),
):
    offset = (page - 1) * page_size
    items, total = harvest_service.list_harvests(
        farm_id=farm_id,
        farmer_id=farmer_id,
        commodity=commodity,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=offset
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    paginated_data = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return ApiResponse(
        success=True,
        message="Daftar hasil panen berhasil diambil.",
        data=paginated_data
    )


@router.get(
    "/{harvest_id}",
    response_model=ApiResponse[HarvestRecordResponse],
    summary="Mengambil detail hasil panen dan KPI",
)
def get_harvest_detail(harvest_id: str):
    record = harvest_service.get_harvest(harvest_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    return ApiResponse(
        success=True,
        message="Detail hasil panen berhasil diambil.",
        data=record
    )


@router.get(
    "/{harvest_id}/report",
    response_class=HTMLResponse,
    summary="Menghasilkan halaman laporan resmi panen siap cetak / simpan ke PDF",
)
def get_harvest_printable_report(harvest_id: str):
    record = harvest_service.get_harvest(harvest_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    html_content = report_service.generate_printable_html(record)
    return HTMLResponse(content=html_content)


@router.patch(
    "/{harvest_id}",
    response_model=ApiResponse[HarvestRecordResponse],
    summary="Memperbarui sebagian data hasil panen",
)
def update_harvest_record(harvest_id: str, payload: HarvestUpdateRequest):
    updated = harvest_service.update_harvest(harvest_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    return ApiResponse(
        success=True,
        message="Data panen berhasil diperbarui.",
        data=updated
    )


@router.delete(
    "/{harvest_id}",
    response_model=ApiResponse[dict],
    summary="Soft delete record panen (Archive)",
)
def delete_harvest_record(harvest_id: str):
    success = harvest_service.delete_harvest(harvest_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    return ApiResponse(
        success=True,
        message="Record panen berhasil diarsipkan (soft delete).",
        data={"harvest_id": harvest_id, "status": "archived"}
    )
