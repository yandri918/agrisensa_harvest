-- =====================================================================
-- AgriSensa Harvest Intelligence - Initial Seed Data (Master & Sample)
-- =====================================================================

-- 1. SEED USERS & FARMERS
INSERT INTO users (user_id, email, full_name, role)
VALUES 
    ('a0000000-0000-0000-0000-000000000001', 'admin@agrisensa.ai', 'Admin AgriSensa', 'admin'),
    ('a0000000-0000-0000-0000-000000000002', 'andriyanto@petani.id', 'Andriyanto', 'petani')
ON CONFLICT (email) DO NOTHING;

INSERT INTO farmers (farmer_id, user_id, farmer_code, full_name, phone_number, village, district, regency, province)
VALUES (
    'f0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000002',
    'USR-028',
    'Andriyanto',
    '081234567890',
    'Sumbang',
    'Sumbang',
    'Banyumas',
    'Jawa Tengah'
) ON CONFLICT (farmer_code) DO NOTHING;

-- 2. SEED COMMODITIES & VARIETIES
INSERT INTO commodities (commodity_id, code, name, category, default_unit)
VALUES 
    ('c0000000-0000-0000-0000-000000000001', 'CABAI_MERAH', 'Cabai Merah', 'hortikultura', 'kg'),
    ('c0000000-0000-0000-0000-000000000002', 'PADI', 'Padi Sawah', 'pangan', 'kg'),
    ('c0000000-0000-0000-0000-000000000003', 'JAGUNG', 'Jagung Pipil', 'pangan', 'kg'),
    ('c0000000-0000-0000-0000-000000000004', 'BAWANG_MERAH', 'Bawang Merah', 'hortikultura', 'kg'),
    ('c0000000-0000-0000-0000-000000000005', 'TOMAT', 'Tomat Buah', 'hortikultura', 'kg')
ON CONFLICT (code) DO NOTHING;

INSERT INTO varieties (variety_id, commodity_id, code, name, potential_yield_ton_per_ha, maturity_days_min, maturity_days_max)
VALUES 
    ('v0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'LADO_F1', 'Lado F1', 18.0, 75, 85),
    ('v0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000001', 'IMPERIAL_10', 'Imperial 10', 20.0, 80, 90),
    ('v0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000002', 'INPARI_32', 'Inpari 32 HDB', 8.5, 115, 120),
    ('v0000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000000004', 'BIMA_BREBES', 'Bima Brebes', 10.0, 55, 60)
ON CONFLICT (code) DO NOTHING;

-- 3. SEED FARMS & SEASONS
INSERT INTO seasons (season_id, season_code, name, start_date, end_date)
VALUES 
    ('s0000000-0000-0000-0000-000000000001', 'SEASON-2026-01', 'Musim Kemarau 1 2026', '2026-05-01', '2026-09-30')
ON CONFLICT (season_code) DO NOTHING;

INSERT INTO farms (farm_id, farmer_id, farm_code, name, total_area_ha, village, district, regency, province, latitude, longitude, altitude_masl, soil_type, farming_system)
VALUES (
    'fa000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    'FARM-001',
    'Kebun Sumbang Makmur',
    0.5000,
    'Sumbang',
    'Sumbang',
    'Banyumas',
    'Jawa Tengah',
    -7.3430000,
    109.2440000,
    450.0,
    'Andosol',
    'konvensional'
) ON CONFLICT (farm_code) DO NOTHING;

-- 4. SEED SAMPLE HARVEST RECORD (Matches Blueprint Section 7 Payload)
INSERT INTO harvests (
    harvest_id,
    idempotency_key,
    farm_id,
    farmer_id,
    season_id,
    commodity_id,
    variety_id,
    planting_date,
    harvest_date,
    harvest_sequence,
    land_area_ha,
    harvest_quantity_kg,
    marketable_quantity_kg,
    damaged_quantity_kg,
    original_quantity,
    original_quantity_unit,
    selling_price_per_kg,
    currency,
    gross_revenue,
    total_production_cost,
    net_profit,
    sales_channel,
    damage_cause,
    field_notes,
    status,
    source
) VALUES (
    'h0000000-0000-0000-0000-000000000001',
    'IDEMP-20260917-CABAI-001',
    'fa000000-0000-0000-0000-000000000001',
    'f0000000-0000-0000-0000-000000000001',
    's0000000-0000-0000-0000-000000000001',
    'c0000000-0000-0000-0000-000000000001',
    'v0000000-0000-0000-0000-000000000001',
    '2026-05-10',
    '2026-09-17',
    3,
    0.5000,
    3250.000,
    2980.000,
    270.000,
    3250.000,
    'kg',
    42000.00,
    'IDR',
    125160000.00, -- 2980 kg * Rp 42.000
    68500000.00,
    56660000.00, -- Revenue - Cost
    'pasar_induk',
    'Antraknosa pada sebagian buah',
    'Panen ketiga dengan mutu dominan grade A',
    'approved',
    'api'
) ON CONFLICT (harvest_id) DO NOTHING;

-- Grades
INSERT INTO harvest_grades (harvest_id, grade_name, quantity_kg, price_per_kg)
VALUES 
    ('h0000000-0000-0000-0000-000000000001', 'A', 1800.000, 45000.00),
    ('h0000000-0000-0000-0000-000000000001', 'B', 850.000, 39000.00),
    ('h0000000-0000-0000-0000-000000000001', 'C', 330.000, 30000.00);

-- Pest & Disease Event
INSERT INTO pest_disease_events (harvest_id, farm_id, pest_disease_name, severity_percent, treatment_applied, observation_date)
VALUES (
    'h0000000-0000-0000-0000-000000000001',
    'fa000000-0000-0000-0000-000000000001',
    'Antraknosa',
    8.00,
    'Sanitasi dan fungisida sesuai SOP',
    '2026-09-15'
);
