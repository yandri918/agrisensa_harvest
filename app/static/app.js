// =====================================================================
// AgriSensa Harvest Intelligence - Interactive Frontend Application
// =====================================================================

const API_BASE = '/api/v1';

// Chart instances
let trendChartInstance = null;
let qualityChartInstance = null;
let financialChartInstance = null;
let commodityChartInstance = null;

// Global harvest records cache
let harvestRecords = [];

// Init on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  fetchDashboardData();
  fetchDriveStatus();
  setupLiveCalculator();
});

function initEventListeners() {
  // Modal buttons
  document.getElementById('openIngestModalBtn').addEventListener('click', openModal);
  document.getElementById('closeModalBtn').addEventListener('click', closeModal);
  document.getElementById('refreshDataBtn').addEventListener('click', fetchDashboardData);

  // Google Drive Modal
  document.getElementById('openDriveConfigBtn').addEventListener('click', openDriveModal);
  document.getElementById('closeDriveModalBtn').addEventListener('click', closeDriveModal);
  document.getElementById('driveConfigForm').addEventListener('submit', handleSaveDriveConfig);
  document.getElementById('testDriveConnBtn').addEventListener('click', handleTestDriveConnection);
  document.getElementById('testDriveUploadBtn').addEventListener('click', handleTestDriveUpload);
  
  // File input reader
  document.getElementById('driveJsonFileInput').addEventListener('change', handleDriveFileSelect);

  // Auto-detect client email on textarea paste/input
  document.getElementById('service_account_json').addEventListener('input', (e) => {
    try {
      const parsed = JSON.parse(e.target.value.trim());
      if (parsed.client_email) {
        showDetectedEmail(parsed.client_email);
      }
    } catch (_) {}
  });

  // Form submit
  document.getElementById('harvestForm').addEventListener('submit', handleHarvestSubmit);

  // Search input
  document.getElementById('searchInput').addEventListener('input', (e) => {
    filterTable(e.target.value);
  });
}

// ---------------------------------------------------------------------
// 1. DATA FETCHING & DASHBOARD REFRESH
// ---------------------------------------------------------------------

async function fetchDashboardData() {
  try {
    // 1. Fetch records
    const resRecords = await fetch(`${API_BASE}/harvests`);
    const dataRecords = await resRecords.json();
    
    if (dataRecords.success) {
      harvestRecords = dataRecords.data.items || [];
      renderTable(harvestRecords);
      renderTrendChart(harvestRecords);
      renderQualityChart(harvestRecords);
      renderFinancialChart(harvestRecords);
      renderCommodityChart(harvestRecords);
    }

    // 2. Fetch summary KPIs
    const resSummary = await fetch(`${API_BASE}/analytics/summary`);
    const dataSummary = await resSummary.json();
    if (dataSummary.success) {
      updateKpiCards(dataSummary.data);
    }

    // Update status badge
    document.getElementById('apiStatusBadge').style.borderColor = 'rgba(16, 185, 129, 0.4)';
    document.getElementById('apiStatusText').textContent = 'API Live (Connected)';

  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    showToast('Gagal memuat data dari API. Memeriksa koneksi...', 'error');
    document.getElementById('apiStatusText').textContent = 'API Offline';
  }
}

// ---------------------------------------------------------------------
// 2. KPI CARDS UPDATE
// ---------------------------------------------------------------------

function updateKpiCards(summary) {
  document.getElementById('kpiTotalHarvest').textContent = `${(summary.total_harvest_kg || 0).toLocaleString('id-ID')} kg`;
  document.getElementById('kpiAvgProductivity').textContent = `${(summary.avg_productivity_kg_per_ha || 0).toLocaleString('id-ID')} kg/ha`;
  document.getElementById('kpiTotalRevenue').textContent = `Rp ${(summary.total_gross_revenue_idr || 0).toLocaleString('id-ID')}`;
  document.getElementById('kpiNetProfit').textContent = `Rp ${(summary.total_net_profit_idr || 0).toLocaleString('id-ID')}`;
  document.getElementById('kpiAvgRoi').textContent = `ROI: ${(summary.avg_roi_percent || 0).toFixed(1)}%`;
  document.getElementById('kpiMarketableYield').textContent = `${(summary.avg_marketable_yield_percent || 0).toFixed(1)}%`;
  document.getElementById('recordCountBadge').textContent = `${summary.total_records || 0} Data Panen`;
}

// ---------------------------------------------------------------------
// 3. TABLE RENDERING & FILTERING
// ---------------------------------------------------------------------

function renderTable(records) {
  const tbody = document.getElementById('harvestTableBody');
  if (!records || records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 32px;">
          Belum ada data panen tercatat. Klik tombol <strong>Input Data Panen</strong> untuk memulai.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const kpi = r.kpi_summary;
    const roi = kpi ? kpi.economic_kpis.roi_percent : 0;
    const shortId = r.harvest_id.length > 10 ? r.harvest_id.substring(0, 8) + '...' : r.harvest_id;

    return `
      <tr>
        <td><code style="color: var(--emerald-400);">${shortId}</code></td>
        <td>
          <strong style="color: var(--text-primary);">${r.commodity}</strong>
          <span style="font-size: 11px; color: var(--text-muted); display: block;">${r.variety || '-'}</span>
        </td>
        <td>
          ${r.farm_id}
          <span style="font-size: 11px; color: var(--text-secondary); display: block;">Petani: ${r.farmer_id}</span>
        </td>
        <td>${r.harvest_date} (Ke-${r.harvest_sequence})</td>
        <td>${r.land_area_ha} ha</td>
        <td><strong>${r.harvest_quantity_kg.toLocaleString('id-ID')} kg</strong></td>
        <td><span style="color: #38bdf8; font-weight: 600;">Rp ${r.net_profit.toLocaleString('id-ID')}</span></td>
        <td><span class="trend-up">${roi.toFixed(1)}%</span></td>
        <td>
          <span class="badge ${r.status === 'approved' ? 'badge-approved' : 'badge-validated'}">
            ${r.status.toUpperCase()}
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary btn-sm" onclick="syncRecord('${r.harvest_id}')" title="Unggah ke Google Drive">
              ☁️ Drive
            </button>
            <button class="btn btn-secondary btn-sm" onclick="viewDetail('${r.harvest_id}')" title="Lihat Detail">
              👁️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function filterTable(keyword) {
  const q = keyword.toLowerCase().trim();
  const filtered = harvestRecords.filter(r => 
    r.commodity.toLowerCase().includes(q) ||
    (r.variety && r.variety.toLowerCase().includes(q)) ||
    r.farm_id.toLowerCase().includes(q) ||
    r.farmer_id.toLowerCase().includes(q) ||
    r.harvest_id.toLowerCase().includes(q)
  );
  renderTable(filtered);
}

// ---------------------------------------------------------------------
// 4. CHART.JS VISUALIZATION RENDERING
// ---------------------------------------------------------------------

function renderTrendChart(records) {
  const ctx = document.getElementById('harvestTrendChart').getContext('2d');
  if (trendChartInstance) trendChartInstance.destroy();

  const labels = records.map((r, i) => `${r.commodity} (${r.harvest_date})`).reverse();
  const quantities = records.map(r => r.harvest_quantity_kg).reverse();
  const productivities = records.map(r => r.kpi_summary ? r.kpi_summary.production_kpis.productivity_kg_per_ha : 0).reverse();

  trendChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Hasil Panen (kg)',
          data: quantities,
          backgroundColor: 'rgba(16, 185, 129, 0.65)',
          borderColor: '#10b981',
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: 'y'
        },
        {
          label: 'Produktivitas (kg/ha)',
          data: productivities,
          type: 'line',
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.15)',
          borderWidth: 2,
          pointBackgroundColor: '#38bdf8',
          yAxisID: 'y1',
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8' } }
      },
      scales: {
        x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
        y: { type: 'linear', position: 'left', ticks: { color: '#10b981' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
        y1: { type: 'linear', position: 'right', ticks: { color: '#38bdf8' }, grid: { drawOnChartArea: false } }
      }
    }
  });
}

function renderQualityChart(records) {
  const ctx = document.getElementById('qualityGradeChart').getContext('2d');
  if (qualityChartInstance) qualityChartInstance.destroy();

  // Aggregate quality grade distribution
  let totalGradeA = 0, totalGradeB = 0, totalGradeC = 0, totalDamaged = 0;

  records.forEach(r => {
    totalDamaged += r.damaged_quantity_kg || 0;
    if (r.quality_grades && r.quality_grades.length > 0) {
      r.quality_grades.forEach(g => {
        if (g.grade === 'A') totalGradeA += g.quantity_kg;
        else if (g.grade === 'B') totalGradeB += g.quantity_kg;
        else totalGradeC += g.quantity_kg;
      });
    } else {
      totalGradeA += r.marketable_quantity_kg * 0.6;
      totalGradeB += r.marketable_quantity_kg * 0.4;
    }
  });

  qualityChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Grade A (Super)', 'Grade B (Standar)', 'Grade C (Lokal)', 'Rusak / Afkir'],
      datasets: [{
        data: [totalGradeA, totalGradeB, totalGradeC, totalDamaged],
        backgroundColor: [
          '#10b981', // emerald
          '#38bdf8', // sky
          '#f59e0b', // amber
          '#f43f5e'  // rose
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } }
      },
      cutout: '70%'
    }
  });
}

function renderFinancialChart(records) {
  const ctx = document.getElementById('financialChart').getContext('2d');
  if (financialChartInstance) financialChartInstance.destroy();

  const labels = records.map(r => r.commodity + ' #' + r.harvest_sequence).reverse();
  const costs = records.map(r => r.total_production_cost).reverse();
  const revenues = records.map(r => r.gross_revenue).reverse();
  const profits = records.map(r => r.net_profit).reverse();

  financialChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Biaya (IDR)', data: costs, backgroundColor: 'rgba(244, 63, 94, 0.7)', borderRadius: 4 },
        { label: 'Omset (IDR)', data: revenues, backgroundColor: 'rgba(16, 185, 129, 0.7)', borderRadius: 4 },
        { label: 'Laba Bersih (IDR)', data: profits, backgroundColor: 'rgba(56, 189, 248, 0.7)', borderRadius: 4 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94a3b8' } } },
      scales: {
        x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
      }
    }
  });
}

function renderCommodityChart(records) {
  const ctx = document.getElementById('commodityChart').getContext('2d');
  if (commodityChartInstance) commodityChartInstance.destroy();

  const commodityMap = {};
  records.forEach(r => {
    if (!commodityMap[r.commodity]) {
      commodityMap[r.commodity] = { totalKg: 0, totalHa: 0 };
    }
    commodityMap[r.commodity].totalKg += r.harvest_quantity_kg;
    commodityMap[r.commodity].totalHa += r.land_area_ha;
  });

  const labels = Object.keys(commodityMap);
  const avgProd = labels.map(k => Math.round(commodityMap[k].totalKg / (commodityMap[k].totalHa || 1)));

  commodityChartInstance = new Chart(ctx, {
    type: 'polarArea',
    data: {
      labels: labels,
      datasets: [{
        data: avgProd,
        backgroundColor: [
          'rgba(16, 185, 129, 0.6)',
          'rgba(56, 189, 248, 0.6)',
          'rgba(245, 158, 11, 0.6)',
          'rgba(167, 139, 250, 0.6)'
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 11 } } }
      },
      scales: {
        r: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { backdropColor: 'transparent', color: '#64748b' } }
      }
    }
  });
}

// ---------------------------------------------------------------------
// 5. LIVE REALTIME KPI CALCULATOR IN MODAL
// ---------------------------------------------------------------------

function setupLiveCalculator() {
  const inputs = [
    'land_area', 'land_area_unit',
    'harvest_quantity', 'quantity_unit',
    'marketable_quantity', 'damaged_quantity',
    'selling_price_per_unit', 'production_cost'
  ];

  inputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', updateLiveCalculation);
      el.addEventListener('change', updateLiveCalculation);
    }
  });
}

function updateLiveCalculation() {
  const landArea = parseFloat(document.getElementById('land_area').value) || 0;
  const landUnit = document.getElementById('land_area_unit').value;
  const harvestQty = parseFloat(document.getElementById('harvest_quantity').value) || 0;
  const qtyUnit = document.getElementById('quantity_unit').value;
  const marketableQty = parseFloat(document.getElementById('marketable_quantity').value) || 0;
  const price = parseFloat(document.getElementById('selling_price_per_unit').value) || 0;
  const cost = parseFloat(document.getElementById('production_cost').value) || 0;

  // Convert area
  let areaHa = landArea;
  if (landUnit === 'm2') areaHa = landArea / 10000;
  else if (landUnit === 'bata') areaHa = landArea * 0.0014;

  // Convert weight
  let qtyKg = harvestQty;
  if (qtyUnit === 'ton') qtyKg = harvestQty * 1000;
  else if (qtyUnit === 'kuintal') qtyKg = harvestQty * 100;
  else if (qtyUnit === 'peti') qtyKg = harvestQty * 30;

  let mQtyKg = marketableQty;
  if (qtyUnit === 'ton') mQtyKg = marketableQty * 1000;
  else if (qtyUnit === 'kuintal') mQtyKg = marketableQty * 100;
  else if (qtyUnit === 'peti') mQtyKg = marketableQty * 30;

  // Calculate live KPIs
  const productivity = areaHa > 0 ? (qtyKg / areaHa) : 0;
  const revenue = mQtyKg * price;
  const profit = revenue - cost;
  const roi = cost > 0 ? ((profit / cost) * 100) : 0;
  const bep = mQtyKg > 0 ? (cost / mQtyKg) : 0;

  // Render to live preview
  document.getElementById('liveCalcProductivity').textContent = `${productivity.toLocaleString('id-ID', { maximumFractionDigits: 2 })} kg/ha`;
  document.getElementById('liveCalcRevenue').textContent = `Rp ${revenue.toLocaleString('id-ID')}`;
  document.getElementById('liveCalcProfit').textContent = `Rp ${profit.toLocaleString('id-ID')}`;
  document.getElementById('liveCalcRoi').textContent = `${roi.toFixed(2)}%`;
  document.getElementById('liveCalcBep').textContent = `Rp ${bep.toLocaleString('id-ID', { maximumFractionDigits: 2 })} / kg`;
}

// ---------------------------------------------------------------------
// 6. FORM SUBMIT & PRESETS
// ---------------------------------------------------------------------

async function handleHarvestSubmit(e) {
  e.preventDefault();

  const payload = {
    farm_id: document.getElementById('farm_id').value,
    farmer_id: document.getElementById('farmer_id').value,
    commodity: document.getElementById('commodity').value,
    variety: document.getElementById('variety').value,
    planting_date: document.getElementById('planting_date').value,
    harvest_date: document.getElementById('harvest_date').value,
    land_area: parseFloat(document.getElementById('land_area').value),
    land_area_unit: document.getElementById('land_area_unit').value,
    harvest_quantity: parseFloat(document.getElementById('harvest_quantity').value),
    quantity_unit: document.getElementById('quantity_unit').value,
    marketable_quantity: parseFloat(document.getElementById('marketable_quantity').value),
    damaged_quantity: parseFloat(document.getElementById('damaged_quantity').value),
    selling_price_per_unit: parseFloat(document.getElementById('selling_price_per_unit').value),
    production_cost: parseFloat(document.getElementById('production_cost').value),
    sales_channel: document.getElementById('sales_channel').value,
    notes: document.getElementById('notes').value
  };

  try {
    const res = await fetch(`${API_BASE}/harvests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (res.ok && result.success) {
      showToast(`Data panen ${payload.commodity} berhasil disimpan dan tervalidasi!`, 'success');
      closeModal();
      fetchDashboardData();
    } else {
      showToast(result.detail || result.message || 'Gagal menyimpan data panen', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Terjadi kesalahan jaringan saat mengirim data.', 'error');
  }
}

function loadPreset(type) {
  if (type === 'cabai') {
    document.getElementById('farm_id').value = 'FARM-001';
    document.getElementById('farmer_id').value = 'USR-028';
    document.getElementById('commodity').value = 'Cabai Merah';
    document.getElementById('variety').value = 'Lado F1';
    document.getElementById('planting_date').value = '2026-05-10';
    document.getElementById('harvest_date').value = '2026-09-17';
    document.getElementById('land_area').value = 0.5;
    document.getElementById('land_area_unit').value = 'ha';
    document.getElementById('harvest_quantity').value = 3250;
    document.getElementById('quantity_unit').value = 'kg';
    document.getElementById('marketable_quantity').value = 2980;
    document.getElementById('damaged_quantity').value = 270;
    document.getElementById('selling_price_per_unit').value = 42000;
    document.getElementById('production_cost').value = 68500000;
    document.getElementById('sales_channel').value = 'pasar_induk';
  } else if (type === 'padi') {
    document.getElementById('farm_id').value = 'FARM-002';
    document.getElementById('farmer_id').value = 'USR-014';
    document.getElementById('commodity').value = 'Padi Sawah';
    document.getElementById('variety').value = 'Inpari 32';
    document.getElementById('planting_date').value = '2026-04-15';
    document.getElementById('harvest_date').value = '2026-08-10';
    document.getElementById('land_area').value = 1.0;
    document.getElementById('land_area_unit').value = 'ha';
    document.getElementById('harvest_quantity').value = 7.8;
    document.getElementById('quantity_unit').value = 'ton';
    document.getElementById('marketable_quantity').value = 7.5;
    document.getElementById('damaged_quantity').value = 0.3;
    document.getElementById('selling_price_per_unit').value = 6500000;
    document.getElementById('production_cost').value = 24000000;
    document.getElementById('sales_channel').value = 'koperasi_desa';
  } else if (type === 'jagung') {
    document.getElementById('farm_id').value = 'FARM-003';
    document.getElementById('farmer_id').value = 'USR-035';
    document.getElementById('commodity').value = 'Jagung Pipil';
    document.getElementById('variety').value = 'NK212';
    document.getElementById('planting_date').value = '2026-05-01';
    document.getElementById('harvest_date').value = '2026-08-25';
    document.getElementById('land_area').value = 0.8;
    document.getElementById('land_area_unit').value = 'ha';
    document.getElementById('harvest_quantity').value = 6400;
    document.getElementById('quantity_unit').value = 'kg';
    document.getElementById('marketable_quantity').value = 6100;
    document.getElementById('damaged_quantity').value = 300;
    document.getElementById('selling_price_per_unit').value = 5200;
    document.getElementById('production_cost').value = 14500000;
    document.getElementById('sales_channel').value = 'pabrik_pakan';
  }

  updateLiveCalculation();
  showToast(`Preset ${type.toUpperCase()} dimuat!`, 'success');
}

// ---------------------------------------------------------------------
// 7. ACTIONS & HELPERS
// ---------------------------------------------------------------------

async function syncRecord(harvestId) {
  // Jika Google Drive belum terhubung, buka modal konfigurasi langsung
  if (!isDriveConnectedGlobal) {
    showToast('⚠️ Google Drive belum terhubung. Silakan masukkan kredensial Service Account terlebih dahulu.', 'error');
    openDriveModal();
    return;
  }

  showToast('⏳ Sedang mengunggah laporan panen ke Google Drive...', 'success');
  try {
    const res = await fetch(`${API_BASE}/harvests/${harvestId}/sync`, { method: 'POST' });
    const result = await res.json();
    if (result.success && result.data && result.data.web_view_link) {
      const data = result.data;
      const driveUrl = data.web_view_link;
      const folder = data.folder_path || 'AgriSensa_Harvest_Reports';
      
      showToast(
        `📁 <strong>${result.message}</strong><br>` +
        `<a href="${driveUrl}" target="_blank" style="color:#38bdf8; text-decoration:underline; font-weight:700; margin-top:6px; display:inline-block; font-size:13px;">🔗 Klik di sini untuk Buka di Google Drive</a><br>` +
        `<span style="font-size:11px; color:#94a3b8;">Folder: ${folder}</span>`,
        'success'
      );
    } else {
      showToast(result.message || 'Gagal menyinkronkan ke Google Drive', 'error');
    }
  } catch (err) {
    showToast('Gagal memicu sinkronisasi Google Drive', 'error');
  }
}

function viewDetail(harvestId) {
  const record = harvestRecords.find(r => r.harvest_id === harvestId);
  if (!record) return;

  const kpi = record.kpi_summary;
  alert(
    `📋 DETAIL PANEN ${record.commodity} (${record.harvest_date})\n` +
    `-----------------------------------------\n` +
    `Kebun: ${record.farm_id} | Petani: ${record.farmer_id}\n` +
    `Luas Lahan: ${record.land_area_ha} ha\n` +
    `Total Hasil: ${record.harvest_quantity_kg.toLocaleString('id-ID')} kg\n` +
    `Layak Jual: ${record.marketable_quantity_kg.toLocaleString('id-ID')} kg\n` +
    `Rusak/Afkir: ${record.damaged_quantity_kg.toLocaleString('id-ID')} kg\n` +
    `Harga Jual: Rp ${record.selling_price_per_kg.toLocaleString('id-ID')}/kg\n` +
    `Omset: Rp ${record.gross_revenue.toLocaleString('id-ID')}\n` +
    `Biaya: Rp ${record.total_production_cost.toLocaleString('id-ID')}\n` +
    `Laba Bersih: Rp ${record.net_profit.toLocaleString('id-ID')}\n` +
    `Produktivitas: ${kpi ? kpi.production_kpis.productivity_kg_per_ha : '-'} kg/ha\n` +
    `ROI: ${kpi ? kpi.economic_kpis.roi_percent : '-'}%\n` +
    `Status: ${record.status}`
  );
}

function openModal() {
  document.getElementById('ingestModal').classList.add('active');
  updateLiveCalculation();
}

function closeModal() {
  document.getElementById('ingestModal').classList.remove('active');
}

// ---------------------------------------------------------------------
// 8. GOOGLE DRIVE CONFIGURATION MODAL & HANDLERS
// ---------------------------------------------------------------------

let isDriveConnectedGlobal = false;

async function fetchDriveStatus() {
  try {
    const res = await fetch(`${API_BASE}/config/google-drive`);
    const data = await res.json();
    if (data.success) {
      const drive = data.data;
      isDriveConnectedGlobal = drive.is_connected;

      const headerText = document.getElementById('headerDriveStatusText');
      const bannerTitle = document.getElementById('driveStatusTitle');
      const bannerSub = document.getElementById('driveStatusSubtitle');
      const banner = document.getElementById('driveConnectionBanner');

      if (drive.is_connected) {
        headerText.innerHTML = `Google Drive <span style="color: var(--emerald-400); font-weight:700;">● Terhubung</span>`;
        bannerTitle.textContent = `🟢 Terhubung Aktif (Google Drive)`;
        bannerTitle.style.color = 'var(--emerald-400)';
        bannerSub.textContent = `Penyimpanan: Folder '${drive.folder_name}' di Google Drive Anda.`;
        banner.style.borderLeftColor = 'var(--emerald-500)';
      } else {
        headerText.innerHTML = `Google Drive <span style="color: var(--amber-500); font-weight:700;">● Belum Terhubung</span>`;
        bannerTitle.textContent = `🟡 Belum Terhubung`;
        bannerTitle.style.color = 'var(--amber-500)';
        bannerSub.textContent = `Ikuti 3 langkah di bawah untuk menghubungkan Google Drive pribadi Anda secara instan.`;
        banner.style.borderLeftColor = 'var(--amber-500)';
      }

      if (drive.folder_name) {
        document.getElementById('drive_folder_name').value = drive.folder_name;
      }
    }
  } catch (err) {
    console.error('Gagal mengambil status Google Drive:', err);
  }
}

function copyAppsScriptCode() {
  const codeEl = document.getElementById('appsScriptTemplateCode');
  if (codeEl) {
    navigator.clipboard.writeText(codeEl.value);
    showToast('📋 Kode Google Apps Script disalin ke clipboard! Tempelkan di script.google.com', 'success');
  }
}

function openDriveModal() {
  document.getElementById('driveConfigModal').classList.add('active');
  fetchDriveStatus();
}

function closeDriveModal() {
  document.getElementById('driveConfigModal').classList.remove('active');
}

async function handleTestDriveConnection() {
  const webhookUrl = document.getElementById('drive_webhook_url').value.trim();
  if (!webhookUrl) {
    showToast('Silakan masukkan Web App URL Google Apps Script Anda terlebih dahulu.', 'error');
    return;
  }

  const btn = document.getElementById('testDriveConnBtn');
  btn.textContent = '⏳ Menguji...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/config/google-drive/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url: webhookUrl })
    });

    const result = await res.json();
    if (res.ok && result.success) {
      showToast(`✅ ${result.message}`, 'success');
    } else {
      showToast(`❌ ${result.detail || result.message || 'Koneksi gagal'}`, 'error');
    }
  } catch (err) {
    showToast('Terjadi kesalahan saat menguji Webhook Google Apps Script.', 'error');
  } finally {
    btn.textContent = '🧪 Test Koneksi';
    btn.disabled = false;
  }
}

async function handleTestDriveUpload() {
  const btn = document.getElementById('testDriveUploadBtn');
  btn.textContent = '⏳ Mengunggah...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/config/google-drive/test-upload`, {
      method: 'POST'
    });

    const result = await res.json();
    if (res.ok && result.success) {
      const link = result.data.web_view_link;
      showToast(`✅ ${result.message} <br><a href="${link}" target="_blank" style="color:#38bdf8; text-decoration:underline; font-weight:700;">🔗 Buka File Test di Google Drive Anda</a>`, 'success');
    } else {
      showToast(`❌ ${result.detail || result.message || 'Upload gagal'}`, 'error');
    }
  } catch (err) {
    showToast('Terjadi kesalahan saat mengunggah file uji coba.', 'error');
  } finally {
    btn.textContent = '📤 Test Upload File';
    btn.disabled = false;
  }
}

async function handleSaveDriveConfig(e) {
  e.preventDefault();

  const webhookUrl = document.getElementById('drive_webhook_url').value.trim();
  const folderName = document.getElementById('drive_folder_name').value.trim();

  if (!webhookUrl) {
    showToast('Silakan masukkan Web App URL Google Apps Script.', 'error');
    return;
  }

  const saveBtn = document.getElementById('saveDriveBtn');
  saveBtn.textContent = '⏳ Menyimpan...';
  saveBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/config/google-drive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        webhook_url: webhookUrl,
        folder_name: folderName || 'AgriSensa_Harvest_Reports'
      })
    });

    const result = await res.json();
    if (res.ok && result.success) {
      showToast(`✅ ${result.message}`, 'success');
      fetchDriveStatus();
      closeDriveModal();
    } else {
      showToast(`❌ ${result.detail || result.message || 'Gagal menyimpan konfigurasi'}`, 'error');
    }
  } catch (err) {
    showToast('Terjadi kesalahan jaringan saat menyimpan konfigurasi.', 'error');
  } finally {
    saveBtn.textContent = '💾 Simpan & Aktifkan';
    saveBtn.disabled = false;
  }
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : '⚠️'}</span>
    <div style="flex:1;">${message}</div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 6000);
}

