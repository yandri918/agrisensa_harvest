# 🌾 AgriSensa Harvest Intelligence & Analytics Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL / Supabase](https://img.shields.io/badge/PostgreSQL-Supabase-3ecf8e.svg?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![Railway Deployment](https://img.shields.io/badge/Deploy-Railway-0B0D0E.svg?style=flat&logo=railway&logoColor=white)](https://railway.com/)
[![PWA Ready](https://img.shields.io/badge/PWA-Offline--First-5A0FC8.svg?style=flat&logo=pwa&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)

**AgriSensa Harvest Intelligence** adalah platform analitik dan rekapitulasi hasil panen cerdas generasi baru yang dirancang untuk agribisnis, kelompok tani, korporasi perkebunan, dan praktisi pertanian modern.

Platform ini mengintegrasikan **Pencatatan Data Lapangan (*Data Ingestion*)**, **Normalisasi Satuan Otomatis**, **Mesin Analitik Finansial & KPI Agronomi**, **AgriSensa AI & Benchmark Evaluator Nasional (Standar Kementan RI & BPS)**, **Laporan Resmi Siap Cetak (Kop PDF Resmi)**, **Dukungan PWA Offline-First Lapangan**, serta **Otomasi Notifikasi Multi-Channel WhatsApp / Webhook**.

---

## 🌐 Akses Live Production & Dokumentasi

- **Dashboard UI Utama:** [https://agrisensa-harvest-api-production.up.railway.app](https://agrisensa-harvest-api-production.up.railway.app)
- **Interactive Swagger API Docs:** [https://agrisensa-harvest-api-production.up.railway.app/docs](https://agrisensa-harvest-api-production.up.railway.app/docs)
- **ReDoc Documentation:** [https://agrisensa-harvest-api-production.up.railway.app/redoc](https://agrisensa-harvest-api-production.up.railway.app/redoc)
- **Health Check Endpoint:** [https://agrisensa-harvest-api-production.up.railway.app/health](https://agrisensa-harvest-api-production.up.railway.app/health)

---

## 🚀 Fitur Unggulan Sistem

### 1. ⚡ Mesin Kalkulasi KPI & Analisis Finansial Otomatis
Setiap data panen yang dicatat langsung dikalkulasi secara instan tanpa perlu perhitungan manual:
- **Produktivitas Lahan ($P$):** Normalisasi satuan lokal (`m²`, `bata/ru` $\rightarrow$ `ha`) dan bobot (`ton`, `kuintal`, `peti` $\rightarrow$ `kg`) untuk menghasilkan produktivitas presisi (kg/ha).
- **Hasil Layak Jual vs Susut (*Marketable Yield vs Loss Rate*):** Menghitung persentase mutu pasar vs susut afkir secara akurat.
- **Finansial Lengkap:** Pendapatan Kotor (*Gross Revenue / Omset*), Biaya Produksi per kg, Laba Bersih (*Net Profit*), *Profit Margin (%)*, *Return on Investment (ROI %)*, *Revenue per Hectare*, dan *Break-Even Price (BEP)* harga impas per kilogram.

---

### 2. 🧠 AgriSensa AI Intelligence & Benchmark Evaluator
Sistem cerdas yang mengevaluasi kinerja budidaya terhadap standar acuan nasional (**Badan Pusat Statistik & Kementerian Pertanian RI**):
- **Formula Deviasi Kinerja Produktivitas ($\Delta P$):**
  $$\Delta P (\%) = \left( \frac{P_{\text{aktual}} - P_{\text{standar}}}{P_{\text{standar}}} \right) \times 100\%$$
- **Weighted Benchmark Multi-Komoditas:** Menghitung standar rata-rata berbobot luas lahan saat memfilter seluruh komoditas sekaligus.
- **Analisis Tingkat Kerusakan (*Loss Rate*) & Diagnosa Hama Riil:** Membandingkan susut fisik dengan batas toleransi komoditas dan mengekstrak data gejala hama dominan (*Antraknosa, Lalat Buah, Blas, Ulat Grayak*, dll.).
- **Agronomic Multi-Criteria Composite Score (0 - 100):** Menghasilkan rating performa objektif (⭐⭐⭐⭐⭐) beserta rekomendasi perbaikan agronomi, pemupukan, dan pasca panen.

---

### 3. 🎨 Dashboard Interaktif & Ergonomis (*Eye-Friendly Glassmorphism*)
- **Palet Warna Teduh & Nyaman di Mata:** Desain modern *Calm Dark Slate* (`#0b0f19`, `#111827`, `#1e293b`) dengan aksen *Soft Emerald* dan tipografi **Plus Jakarta Sans** + **Outfit**.
- **Panel Filter Dinamis & Reaktif:** Filter komoditas, periode cepat (30 hari, 90 hari musim ini, 1 tahun), atau rentang tanggal kustom yang secara langsung memperbarui 6 kartu KPI ringkasan dan 4 grafik visualisasi **Chart.js** interaktif.
- **Alur Persetujuan Data 1-Klik (*Approval Lifecycle*):**
  - Tombol cepat **`✓ Setujui`** untuk manajer kebun langsung di tabel.
  - Dropdown selector status interaktif (`🔵 VALIDATED`, `🟢 APPROVED`, `🟠 REVIEW`, `⚪ DRAFT`).

---

### 4. 📄 Laporan Resmi Cetak / Simpan PDF dengan Kop Surat
- **Kop Surat Standar Agribisnis Resmi:** Dilengkapi emblem brand padi (`🌾`), nama sistem `AGRISENSA HARVEST INTELLIGENCE`, legalitas standar acuan Kementan & BPS, garis ganda resmi (*double divider*), nomor registrasi dokumen (`HARV-XXXXXXXX`), dan tanggal cetak berstempel waktu Indonesia (`WIB`).
- **Layout Cetak Presisi (A4 Portrait):** Dioptimalkan dengan CSS `@media print` (`page-break-inside: avoid` dan `-webkit-print-color-adjust: exact`) sehingga tidak terpotong saat dicetak atau disimpan sebagai PDF.

---

### 5. 📥 Ekspor Rekapitulasi Excel / CSV (1-Klik)
- Mengunduh seluruh rekapitulasi data panen lengkap (identitas kebun, tanggal, luas, volume, omset, biaya, laba bersih, ROI, BEP, produktivitas, dan status) ke format **CSV/Excel** dengan *UTF-8 Byte Order Mark (BOM)* agar karakter rupiah dan angka langsung rapi di Microsoft Excel.
- Mendukung filter ekspor dinamis berdasarkan komoditas dan rentang tanggal.

---

### 6. 📡 PWA Offline-First (Pencatatan Lapangan Tanpa Sinyal)
- **Service Worker Caching (Network-First `v3.3`):** Aplikasi web dapat diakses dan diinstal layaknya aplikasi native di Android, iOS, dan Desktop.
- **Offline Storage Queue:** Petani dan mandor di pedalaman/kebun tanpa sinyal internet tetap dapat menginput data panen. Data disimpan secara aman di *Local Queue* perangkat dan akan **otomatis tersinkronisasi ke server cloud** saat perangkat kembali online.

---

### 7. 🔔 Otomasi Notifikasi WhatsApp & Multi-Channel Webhook
- Integrasi otomatis dengan gateway pesan instan (**WhatsApp Gateway: Fonnte, Wablas, Waha, UltraMsg**, Discord, Telegram, Slack, atau n8n).
- Setiap ada panen baru yang dicatat, sistem dapat mengirimkan ringkasan hasil panen, omset, laba, dan evaluasi rating AI secara otomatis ke nomor WhatsApp pemilik kebun atau grup koordinasi mandor.

---

## 📁 Struktur Proyek

```text
agrisensa_harvest/
├── database/
│   ├── 01_schema.sql            # DDL PostgreSQL / Supabase + PostGIS (16 tabel relasional & trigger)
│   └── 02_seeds.sql             # Data master komoditas, varietas, petani, kebun & data panen
├── app/
│   ├── main.py                  # Entrypoint FastAPI, CORS, middleware & routing
│   ├── config.py                # Konfigurasi aplikasi, env vars & parameter database
│   ├── schemas/                 # Kontrak data Pydantic v2
│   │   ├── common.py            # Response envelope standar & Enum status
│   │   ├── harvest.py           # Skema payload Ingest, Update, dan Query Panen
│   │   └── kpi.py               # Skema indikator produksi & finansial
│   ├── services/                # Logika bisnis & analitik inti
│   │   ├── normalizer.py        # Normalisasi satuan luas (m2/bata -> ha) & bobot (ton/peti -> kg)
│   │   ├── validator.py         # Validasi konsistensi tanggal, kuantitas & aturan bisnis
│   │   ├── analytics_service.py # Kalkulator KPI (Produktivitas, Margin, BEP, ROI, Loss)
│   │   ├── ai_insight_service.py # Mesin AI evaluasi benchmark BPS/Kementan & rekomendasi
│   │   ├── harvest_service.py   # CRUD repository, storage layer & idempotency engine
│   │   ├── report_service.py    # Generator lembar laporan HTML / Kop PDF resmi
│   │   ├── notification_service.py # Webhook dispatcher (WhatsApp / Discord / Telegram)
│   │   └── google_drive_service.py # Integrasi arsip cloud Google Workspace / Drive
│   ├── routers/                 # REST API Router Endpoints
│   │   ├── harvests.py          # /api/v1/harvests (Ingest, Query, Export CSV, Cetak PDF, PATCH Status)
│   │   ├── analytics.py         # /api/v1/analytics (KPI Overview, Summary & AI Insights)
│   │   └── config.py            # /api/v1/config (Konfigurasi Webhook & Google Drive)
│   └── static/                  # Frontend Dashboard (PWA Glassmorphism)
│       ├── index.html           # Struktur antarmuka dashboard utama
│       ├── style.css            # Desain sistem eye-friendly & CSS print layout
│       ├── app.js               # Logika interaktif, reactive charts, sync & calculator
│       ├── sw.js                # Service Worker PWA offline caching
│       └── manifest.json        # Manifest web app installable
├── tests/                       # Test suite otomatis
│   ├── verify_standalone.py     # Pengujian unit formula normalisasi & KPI
│   ├── verify_api_endpoints.py  # Pengujian integrasi endpoint HTTP FastAPI
│   └── test_api_and_kpis.py     # Pytest test suite
├── railway.json                 # Konfigurasi deployment Railway
├── Procfile                     # Process file untuk production server
├── requirements.txt             # Dependensi Python production
└── README.md                    # Dokumentasi utama proyek
```

---

## 🛠️ Instalasi & Menjalankan Lokal

### 1. Kloning Repositori
```bash
git clone https://github.com/yandri918/agrisensa_harvest.git
cd agrisensa_harvest
```

### 2. Buat Virtual Environment & Install Dependensi
```bash
# Membuat environment Python
python -m venv .venv

# Aktivasi di Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Atau di Linux / macOS:
# source .venv/bin/activate

# Install dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables (`.env`)
Salin file contoh dan sesuaikan konfigurasi Anda:
```bash
cp .env.example .env
```

Contoh isi file `.env`:
```env
APP_NAME=AgriSensa Harvest Intelligence
APP_ENV=development
PORT=8000
DATABASE_URL=postgresql://postgres:password@localhost:5432/agrisensa
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
ENABLE_AUTO_DRIVE_UPLOAD=false
```

### 4. Menjalankan Server Pengembangan
```bash
py -m uvicorn app.main:app --reload --port 8000
```
Buka browser di: **`http://127.0.0.1:8000`**

---

## 🧪 Menjalankan Pengujian (Testing)

```bash
# 1. Menjalankan verifikasi formula matematika KPI & aturan bisnis
python tests/verify_standalone.py

# 2. Menjalankan pengujian endpoint HTTP API
python tests/verify_api_endpoints.py

# 3. Menjalankan test suite menggunakan pytest
pytest tests/test_api_and_kpis.py -v
```

---

## 📖 Ringkasan REST API Endpoints

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `POST` | `/api/v1/harvests` | Mencatat data panen baru (*Data Ingestion & Live Validation*) |
| `GET` | `/api/v1/harvests` | Mengambil daftar riwayat panen (dengan filter komoditas, kebun, tanggal) |
| `GET` | `/api/v1/harvests/{id}` | Mengambil detail spesifik data panen beserta seluruh kalkulasi KPI |
| `PATCH` | `/api/v1/harvests/{id}` | Memperbarui sebagian data panen atau mengubah status (*Approval Lifecycle*) |
| `DELETE`| `/api/v1/harvests/{id}` | Mengarsipkan data panen (*Soft Delete*) |
| `GET` | `/api/v1/harvests/export/csv` | Mengunduh rekapitulasi data panen dalam format **Excel / CSV (UTF-8 BOM)** |
| `GET` | `/api/v1/harvests/{id}/report`| Menghasilkan dokumen **Laporan Resmi Siap Cetak / Simpan PDF** dengan Kop |
| `GET` | `/api/v1/analytics/summary` | Mengambil agregasi metrik (Total kg, Luas ha, Omset, Laba, Rata-rata ROI) |
| `GET` | `/api/v1/analytics/ai-insights` | Evaluasi cerdas AI Benchmark (Deviasi Kinerja, Susut, Rating Bintang) |
| `GET` | `/api/v1/config/notifications` | Mengambil konfigurasi URL Webhook & WhatsApp Gateway |
| `POST` | `/api/v1/config/notifications` | Menyimpan konfigurasi URL Webhook notifikasi otomatis |
| `POST` | `/api/v1/config/notifications/test` | Mengirim pesan uji coba notifikasi ke Webhook |
| `GET` | `/health` | Health check konektivitas database & server |

---

## 🚢 Panduan Deployment

### Deployment ke Railway (Rekomendasi)
Repositori ini telah dilengkapi dengan `railway.json` dan `Procfile` siap pakai.
```bash
# Login ke Railway CLI
railway login

# Deploy langsung dari direktori proyek
railway up --service agrisensa-harvest-api
```

---

## 📜 Lisensi & Hak Cipta
Dikembangkan oleh Tim **AgriSensa** &copy; 2026. Seluruh hak cipta dilindungi undang-undang.
Didedikasikan untuk kemajuan agribisnis dan digitalisasi pertanian Indonesia. 🌾🇮🇩
