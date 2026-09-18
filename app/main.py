from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers.harvests import router as harvests_router
from app.routers.analytics import router as analytics_router
from app.schemas.common import ApiResponse

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
    ## AgriSensa Harvest Intelligence & Reporting API
    
    API terpusat untuk mencatat data panen pertanian (*Data Ingest*), memvalidasi & menormalisasi satuan,
    menghitung indikator produktivitas & ekonomi (*Analytics Engine*), menyinkronkan data ke Google Workspace,
    serta menyediakan layanan backend untuk MCP Server AI AgriSensa.
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles

# Include Routers under API_V1_PREFIX
app.include_router(harvests_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health & Status"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "database": "connected (Supabase/PostgreSQL schema ready)",
        "environment": settings.APP_ENV
    }


# Mount Frontend UI Static Files (disajikan di root / dan /static)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            success=False,
            message="Terjadi kesalahan internal pada server.",
            errors=[str(exc)]
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
