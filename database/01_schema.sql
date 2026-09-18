-- =====================================================================
-- AgriSensa Harvest Intelligence & Reporting - Database Schema (DDL)
-- Target: PostgreSQL 14+ / Supabase (with PostGIS & UUID extensions)
-- Version: 1.0 (Phase 1)
-- =====================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 2. CUSTOM TYPES / ENUMS
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('petani', 'field_officer', 'analyst', 'manager', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE data_source_enum AS ENUM ('web', 'mobile', 'sheets', 'api', 'import');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE harvest_status_enum AS ENUM (
        'draft',
        'submitted',
        'validated',
        'needs_review',
        'approved',
        'synced',
        'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sync_status_enum AS ENUM ('pending', 'processing', 'success', 'failed', 'retry');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE report_status_enum AS ENUM ('queued', 'processing', 'completed', 'failed', 'expired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. MASTER TABLES

-- 3.1 Users & Authorization
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50),
    role user_role_enum NOT NULL DEFAULT 'petani',
    organization_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3.2 Farmers Profile
CREATE TABLE IF NOT EXISTS farmers (
    farmer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    farmer_code VARCHAR(50) UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    nik VARCHAR(30),
    phone_number VARCHAR(50),
    village VARCHAR(100),
    district VARCHAR(100),
    regency VARCHAR(100),
    province VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3.3 Farms & Plots
CREATE TABLE IF NOT EXISTS farms (
    farm_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farmer_id UUID NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    farm_code VARCHAR(50) UNIQUE,
    name VARCHAR(255) NOT NULL,
    total_area_ha NUMERIC(10, 4) NOT NULL CHECK (total_area_ha > 0),
    village VARCHAR(100),
    district VARCHAR(100),
    regency VARCHAR(100),
    province VARCHAR(100),
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    altitude_masl NUMERIC(8, 2),
    soil_type VARCHAR(100),
    farming_system VARCHAR(100) DEFAULT 'konvensional', -- konvensional, organik, hidroponik, greenhouse
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plots (
    plot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    plot_code VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    area_ha NUMERIC(10, 4) NOT NULL CHECK (area_ha > 0),
    polygon_boundary GEOMETRY(Polygon, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3.4 Master Commodities & Varieties
CREATE TABLE IF NOT EXISTS commodities (
    commodity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100), -- hortikultura, pangan, perkebunan
    default_unit VARCHAR(20) DEFAULT 'kg',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS varieties (
    variety_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commodity_id UUID NOT NULL REFERENCES commodities(commodity_id) ON DELETE CASCADE,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    potential_yield_ton_per_ha NUMERIC(8, 2),
    maturity_days_min INT,
    maturity_days_max INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3.5 Seasons / Planting Cycles
CREATE TABLE IF NOT EXISTS seasons (
    season_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    season_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. CORE HARVEST TRANSACTIONS

CREATE TABLE IF NOT EXISTS harvests (
    harvest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    idempotency_key VARCHAR(100) UNIQUE,
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE RESTRICT,
    plot_id UUID REFERENCES plots(plot_id) ON DELETE SET NULL,
    farmer_id UUID NOT NULL REFERENCES farmers(farmer_id) ON DELETE RESTRICT,
    season_id UUID REFERENCES seasons(season_id) ON DELETE SET NULL,
    commodity_id UUID NOT NULL REFERENCES commodities(commodity_id) ON DELETE RESTRICT,
    variety_id UUID REFERENCES varieties(variety_id) ON DELETE RESTRICT,
    
    -- Tanggal & Siklus
    planting_date DATE NOT NULL,
    harvest_date DATE NOT NULL,
    harvest_sequence INT DEFAULT 1 CHECK (harvest_sequence >= 1),
    
    -- Populasi & Luas
    land_area_ha NUMERIC(10, 4) NOT NULL CHECK (land_area_ha > 0),
    initial_plant_population INT,
    productive_plant_population INT,
    
    -- Kuantitas Panen (Satuan Baku kg)
    harvest_quantity_kg NUMERIC(12, 3) NOT NULL CHECK (harvest_quantity_kg >= 0),
    marketable_quantity_kg NUMERIC(12, 3) NOT NULL CHECK (marketable_quantity_kg >= 0),
    damaged_quantity_kg NUMERIC(12, 3) NOT NULL DEFAULT 0 CHECK (damaged_quantity_kg >= 0),
    
    -- Satuan Asli Input
    original_quantity NUMERIC(12, 3),
    original_quantity_unit VARCHAR(30) DEFAULT 'kg',
    
    -- Keuangan
    selling_price_per_kg NUMERIC(14, 2) DEFAULT 0 CHECK (selling_price_per_kg >= 0),
    currency VARCHAR(5) DEFAULT 'IDR',
    gross_revenue NUMERIC(16, 2) DEFAULT 0 CHECK (gross_revenue >= 0),
    total_production_cost NUMERIC(16, 2) DEFAULT 0 CHECK (total_production_cost >= 0),
    net_profit NUMERIC(16, 2) DEFAULT 0,
    
    -- Saluran & Catatan
    sales_channel VARCHAR(100), -- pasar_induk, supermarket, tengkulak, langsung, dll.
    damage_cause TEXT,
    photo_urls TEXT[],
    field_notes TEXT,
    
    -- Status & Audit
    status harvest_status_enum NOT NULL DEFAULT 'submitted',
    source data_source_enum NOT NULL DEFAULT 'api',
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Validasi Konsistensi
    CONSTRAINT check_harvest_date_valid CHECK (harvest_date >= planting_date),
    CONSTRAINT check_marketable_damaged CHECK (marketable_quantity_kg + damaged_quantity_kg <= harvest_quantity_kg + 0.001)
);

-- 4.1 Rincian Grade Mutu Panen
CREATE TABLE IF NOT EXISTS harvest_grades (
    grade_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    harvest_id UUID NOT NULL REFERENCES harvests(harvest_id) ON DELETE CASCADE,
    grade_name VARCHAR(50) NOT NULL, -- Grade A, Grade B, Grade C, Grade Khusus
    quantity_kg NUMERIC(12, 3) NOT NULL CHECK (quantity_kg >= 0),
    price_per_kg NUMERIC(14, 2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.2 Rincian Biaya Produksi
CREATE TABLE IF NOT EXISTS production_costs (
    cost_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    harvest_id UUID NOT NULL REFERENCES harvests(harvest_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- bibit, pupuk, pestisida, tenaga_kerja, irigasi, sewa_lahan, kemasan, transportasi, pascapanen, lainnya
    description VARCHAR(255),
    amount NUMERIC(16, 2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(5) DEFAULT 'IDR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.3 Rincian Penjualan
CREATE TABLE IF NOT EXISTS sales (
    sale_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    harvest_id UUID NOT NULL REFERENCES harvests(harvest_id) ON DELETE CASCADE,
    buyer_name VARCHAR(255),
    market_type VARCHAR(100), -- lokal, pasar_induk, supermarket, industri, ekspor, direct_to_consumer
    quantity_kg NUMERIC(12, 3) NOT NULL CHECK (quantity_kg > 0),
    unit_price NUMERIC(14, 2) NOT NULL CHECK (unit_price >= 0),
    total_amount NUMERIC(16, 2) NOT NULL CHECK (total_amount >= 0),
    payment_method VARCHAR(50),
    sale_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. OBSERVATIONS & EXTERNAL FACTORS

-- 5.1 Kejadian Hama & Penyakit
CREATE TABLE IF NOT EXISTS pest_disease_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    harvest_id UUID REFERENCES harvests(harvest_id) ON DELETE CASCADE,
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    pest_disease_name VARCHAR(150) NOT NULL,
    severity_percent NUMERIC(5, 2) CHECK (severity_percent >= 0 AND severity_percent <= 100),
    affected_area_ha NUMERIC(10, 4),
    treatment_applied TEXT,
    observation_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5.2 Observasi Cuaca
CREATE TABLE IF NOT EXISTS weather_observations (
    weather_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    observation_date DATE NOT NULL,
    temp_min_c NUMERIC(4, 1),
    temp_max_c NUMERIC(4, 1),
    rainfall_mm NUMERIC(7, 2),
    humidity_percent NUMERIC(5, 2),
    extreme_event_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. SYNC & WORKSPACE INTEGRATION

CREATE TABLE IF NOT EXISTS sync_jobs (
    sync_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    harvest_id UUID NOT NULL REFERENCES harvests(harvest_id) ON DELETE CASCADE,
    target_service VARCHAR(50) NOT NULL, -- 'google_sheets', 'n8n_webhook', 'erp'
    target_resource_id VARCHAR(255), -- Sheet ID or Webhook ID
    sheet_name VARCHAR(100),
    row_index INT,
    status sync_status_enum NOT NULL DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    last_error TEXT,
    synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_code VARCHAR(100) UNIQUE NOT NULL,
    harvest_id UUID REFERENCES harvests(harvest_id) ON DELETE SET NULL,
    farm_id UUID REFERENCES farms(farm_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    period VARCHAR(50),
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    storage_path TEXT,
    google_drive_file_id VARCHAR(255),
    google_drive_url TEXT,
    download_signed_url TEXT,
    url_expires_at TIMESTAMPTZ,
    status report_status_enum NOT NULL DEFAULT 'queued',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. AUDIT LOGS

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(100) NOT NULL, -- 'harvests', 'users', 'sync_jobs'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE', 'VALIDATE', 'SYNC'
    actor_id UUID REFERENCES users(user_id),
    actor_role VARCHAR(50),
    source data_source_enum DEFAULT 'api',
    old_data JSONB,
    new_data JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. INDEXES FOR HIGH QUERY PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_harvests_farm_date ON harvests(farm_id, harvest_date DESC);
CREATE INDEX IF NOT EXISTS idx_harvests_commodity ON harvests(commodity_id);
CREATE INDEX IF NOT EXISTS idx_harvests_status ON harvests(status);
CREATE INDEX IF NOT EXISTS idx_harvests_farmer ON harvests(farmer_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_reports_code ON reports(report_code);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_name, entity_id);

-- 9. TRIGGERS FOR auto UPDATED_AT
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE OR REPLACE TRIGGER trg_farmers_updated_at BEFORE UPDATE ON farmers FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE OR REPLACE TRIGGER trg_farms_updated_at BEFORE UPDATE ON farms FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE OR REPLACE TRIGGER trg_harvests_updated_at BEFORE UPDATE ON harvests FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE OR REPLACE TRIGGER trg_sync_jobs_updated_at BEFORE UPDATE ON sync_jobs FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
CREATE OR REPLACE TRIGGER trg_reports_updated_at BEFORE UPDATE ON reports FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
