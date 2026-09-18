from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.common import ApiResponse, PaginatedResponse, HarvestStatusEnum
from app.schemas.harvest import (
    HarvestCreateRequest,
    HarvestUpdateRequest,
    HarvestRecordResponse,
)
from app.services.harvest_service import harvest_service

router = APIRouter(prefix="/harvests", tags=["Harvest Ingest & Management"])


@router.post(
    "",
    response_model=ApiResponse[HarvestRecordResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Mencatat data hasil panen baru (Data Ingest)",
    description="Menerima, memvalidasi, menormalisasi unit, menghitung KPI otomatis, dan menyimpan data hasil panen."
)
def create_harvest_record(payload: HarvestCreateRequest):
    try:
        record, is_new = harvest_service.create_harvest(payload)
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


from app.services.google_drive_service import google_drive_service


@router.post(
    "/{harvest_id}/sync",
    response_model=ApiResponse[dict],
    summary="Sinkronisasi dan unggah laporan hasil panen ke Google Drive",
)
def trigger_sync_harvest(harvest_id: str):
    record = harvest_service.get_harvest(harvest_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record panen dengan ID '{harvest_id}' tidak ditemukan."
        )
    
    # Unggah laporan panen ke Google Drive
    drive_result = google_drive_service.upload_harvest_report(record)
    
    return ApiResponse(
        success=drive_result.get("success", True),
        message=drive_result.get("message", "Sinkronisasi Google Drive selesai."),
        data={
            "harvest_id": harvest_id,
            "target": "Google Drive",
            "drive_status": drive_result.get("mode", "simulation"),
            "file_id": drive_result.get("file_id"),
            "file_name": drive_result.get("file_name"),
            "folder_path": drive_result.get("folder_path"),
            "web_view_link": drive_result.get("web_view_link"),
            "details": drive_result
        }
    )

