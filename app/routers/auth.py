from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.schemas.common import ApiResponse
from app.services.clerk_auth import get_current_user, AuthUser
from app.services.db import db_manager

router = APIRouter(prefix="/auth", tags=["Clerk Authentication & User Profile"])


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    image_url: Optional[str] = None
    role: str
    is_authenticated: bool
    stats: Dict[str, Any]


@router.get(
    "/me",
    response_model=ApiResponse[UserProfileResponse],
    summary="Mengambil profil pengguna yang sedang login & statistik database personal",
    description="Memvalidasi token sesi Clerk dan mengembalikan metadata pengguna serta ringkasan data panen miliknya."
)
async def get_my_profile(current_user: AuthUser = Depends(get_current_user)):
    user_stats = db_manager.get_user_stats(current_user.user_id)
    
    response_data = UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        image_url=current_user.image_url,
        role=current_user.role,
        is_authenticated=current_user.is_authenticated,
        stats=user_stats.get("stats", {})
    )

    return ApiResponse(
        success=True,
        message="Profil akun terdaftar berhasil diverifikasi.",
        data=response_data
    )


@router.post(
    "/sync",
    response_model=ApiResponse[UserProfileResponse],
    summary="Sinkronisasi akun saat pengguna login melalui Clerk",
)
async def sync_user_account(current_user: AuthUser = Depends(get_current_user)):
    db_manager.upsert_user(current_user)
    user_stats = db_manager.get_user_stats(current_user.user_id)

    response_data = UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        image_url=current_user.image_url,
        role=current_user.role,
        is_authenticated=current_user.is_authenticated,
        stats=user_stats.get("stats", {})
    )

    return ApiResponse(
        success=True,
        message="Akun berhasil disinkronkan ke database lokal.",
        data=response_data
    )
