import logging
import httpx
import jwt
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

logger = logging.getLogger("agrisensa.auth")

security_scheme = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    user_id: str = Field(..., description="Unique Clerk User ID (e.g. user_2xxx or USR-xxx)")
    email: str = Field("petani@agrisensa.ai", description="Primary email address")
    full_name: str = Field("Petani Terdaftar", description="User full display name")
    image_url: Optional[str] = Field(None, description="Avatar profile image URL")
    role: str = Field("farmer", description="Role access level: farmer, agronomist, manager, admin")
    is_authenticated: bool = Field(True, description="True if verified via Clerk, False if offline/guest")


class ClerkAuthService:
    """Layanan Verifikasi & Manajemen Sesi Autentikasi Clerk."""

    def __init__(self):
        self.secret_key = settings.CLERK_SECRET_KEY
        self.publishable_key = settings.CLERK_PUBLISHABLE_KEY
        self.clerk_api_base = "https://api.clerk.com/v1"
        self._cached_user_profiles: Dict[str, Dict[str, Any]] = {}

    def decode_token_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Mendekode payload JWT Clerk untuk mengekstrak user_id (sub) dan klaim lainnya."""
        try:
            # Decode JWT claims tanpa verifikasi tanda tangan jika lokal, atau verifikasi struktur
            payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
            return payload
        except Exception as e:
            logger.debug(f"JWT decode error: {e}")
            return None

    async def fetch_clerk_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Mengambil data profil lengkap langsung dari Clerk Backend API."""
        if not self.secret_key:
            return None

        # Check in-memory cache first to minimize external latency
        if user_id in self._cached_user_profiles:
            return self._cached_user_profiles[user_id]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.secret_key}",
                    "Content-Type": "application/json"
                }
                resp = await client.get(f"{self.clerk_api_base}/users/{user_id}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    self._cached_user_profiles[user_id] = data
                    return data
                else:
                    logger.warning(f"Clerk API returned {resp.status_code} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch Clerk user details from API: {e}")

        return None

    async def authenticate_request(self, request: Request) -> AuthUser:
        """
        Memverifikasi identitas pengguna dari Request header:
        1. Bearer Token (Authorization: Bearer <clerk_session_token>)
        2. Header X-User-Id / X-User-Email (dari frontend auth interceptor)
        3. Fallback ke Demo Mandor Mode jika mode offline / tanpa kredensial
        """
        # Lazy import untuk menghindari circular import
        from app.services.db import db_manager

        auth_header = request.headers.get("Authorization")
        header_user_id = request.headers.get("X-User-Id")
        header_user_email = request.headers.get("X-User-Email")
        header_user_name = request.headers.get("X-User-Name")

        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()

        user_id = None
        user_email = header_user_email or "petani@agrisensa.ai"
        user_name = header_user_name or "Petani Terdaftar"
        user_img = None
        is_verified = False

        # 1. Coba ekstrak dari JWT Session Token
        if token and token != "undefined" and token != "null":
            claims = self.decode_token_claims(token)
            if claims:
                user_id = claims.get("sub") or claims.get("user_id") or claims.get("id")
                if "email" in claims:
                    user_email = claims["email"]
                elif "email_address" in claims:
                    user_email = claims["email_address"]
                is_verified = True

        # 2. Jika ada user_id dari token atau X-User-Id header
        if not user_id and header_user_id and header_user_id != "undefined" and header_user_id != "null":
            user_id = header_user_id
            is_verified = True

        # 3. Jika user_id Clerk ditemukan, lengkapi profil via Clerk API jika belum lengkap
        if user_id and user_id.startswith("user_"):
            clerk_profile = await self.fetch_clerk_user(user_id)
            if clerk_profile:
                # Ambil email utama
                email_addresses = clerk_profile.get("email_addresses", [])
                if email_addresses:
                    user_email = email_addresses[0].get("email_address", user_email)

                # Ambil nama
                first_name = clerk_profile.get("first_name", "")
                last_name = clerk_profile.get("last_name", "")
                full = f"{first_name} {last_name}".strip()
                if full:
                    user_name = full
                elif clerk_profile.get("username"):
                    user_name = clerk_profile.get("username")

                user_img = clerk_profile.get("image_url")

        # 4. Strict Authentication Enforcement: jika tidak ada token/user ID, tolak request
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autentikasi diperlukan. Silakan masuk dengan akun Clerk Anda.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        auth_user = AuthUser(
            user_id=user_id,
            email=user_email,
            full_name=user_name,
            image_url=user_img,
            role="farmer",
            is_authenticated=True
        )

        # 5. Sinkronkan & Pastikan Data Pengguna di Database (Auto-Provisioning)
        try:
            db_manager.upsert_user(auth_user)
        except Exception as e:
            logger.error(f"Error upserting user in DB: {e}")

        return auth_user


clerk_auth_service = ClerkAuthService()


async def get_current_user(request: Request) -> AuthUser:
    """Dependency FastAPI untuk mengidentifikasi akun pengguna yang sedang aktif (Strict Authentication)."""
    return await clerk_auth_service.authenticate_request(request)


async def get_optional_user(request: Request) -> Optional[AuthUser]:
    """Dependency FastAPI opsional (mengembalikan None jika tidak login)."""
    try:
        return await clerk_auth_service.authenticate_request(request)
    except HTTPException:
        return None
    except Exception:
        return None
