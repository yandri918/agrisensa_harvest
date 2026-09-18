# AgriSensa Harvest Intelligence & Reporting

Backend service & skema database untuk modul **AgriSensa Harvest Intelligence & Reporting** (Fase 1).

Modul ini bertanggung jawab untuk mencatat data panen (*Data Ingest*), validasi & normalisasi satuan ke standar analitik (`kg` & `ha`), menghitung indikator produktivitas dan ekonomi (*Analytics Engine*), menyinkronkan data ke Google Workspace, serta menjadi fondasi untuk AgriSensa MCP Server.

---

## 📁 Struktur Folder

```text
agrisensa_harvest/
├── database/
│   ├── 01_schema.sql         # DDL skema database PostgreSQL / Supabase + PostGIS (16 tabel)
│   └── 02_seeds.sql          # Data master awal & record uji coba
├── app/
│   ├── config.py             # Konfigurasi aplikasi & environment
│   ├── main.py               # FastAPI entrypoint, middleware CORS, docs
│   ├── schemas/              # Pydantic v2 schemas (kontrak data & validasi)
│   │   ├── common.py         # Response envelope standar & enum status
│   │   ├── harvest.py        # Ingest payload, update request, response
│   │   └── kpi.py            # Indikator produksi & ekonomi
│   ├── services/             # Logika bisnis & kalkulasi analitik
│   │   ├── normalizer.py     # Konverter satuan luas (m2/bata -> ha) & berat (ton/peti -> kg)
│   │   ├── validator.py      # Pemeriksaan konsistensi bisnis & tanggal
│   │   ├── analytics_service.py # Kalkulator KPI (Produktivitas, Margin, BEP, ROI)
│   │   └── harvest_service.py   # Service CRUD, storage layer & idempotency
│   └── routers/              # REST API Endpoints
│       ├── harvests.py       # Endpoints /api/v1/harvests (Ingest, Query, Sync, Delete)
│       └── analytics.py      # Endpoints /api/v1/analytics (KPI & Agregasi)
├── tests/
│   ├── verify_standalone.py  # Test suite mandiri untuk normalisasi & KPI
│   ├── verify_api_endpoints.py # Test suite integrasi HTTP TestClient
│   └── test_api_and_kpis.py  # Pytest test suite
├── .env.example
├── requirements.txt
└── AgriSensa_Harvest_Intelligence_MCP_Architecture.md # Blueprint arsitektur lengkap
```

---

## 🚀 Cara Menjalankan API

### 1. Menyiapkan Virtual Environment & Dependensi
```bash
# Buat dan aktifkan venv (opsional)
python -m venv .venv
.venv\Scripts\activate

# Install dependensi
pip install -r requirements.txt
```

### 2. Menjalankan Server FastAPI
```bash
py -m uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🗄️ Menjalankan Skema Database (PostgreSQL / Supabase)

Eksekusi file SQL berikut di PostgreSQL / Supabase SQL Editor:
1. `database/01_schema.sql` — Membuat ekstensi, enum type, 16 tabel relasional, indeks, dan trigger otomatis `updated_at`.
2. `database/02_seeds.sql` — Mengisi data master komoditas, varietas, petani, kebun, dan data uji coba panen.

---

## 🧪 Menjalankan Pengujian

```bash
# Menjalankan verifikasi formula KPI dan aturan bisnis
py tests/verify_standalone.py

# Menjalankan pengujian endpoint HTTP API
py tests/verify_api_endpoints.py
```
