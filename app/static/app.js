// =====================================================================
// AgriSensa Harvest Intelligence - Interactive Frontend Application
// =====================================================================

const API_BASE = '/api/v1';
const CLERK_PUBLISHABLE_KEY = 'pk_test_dm9jYWwtc2Vhc25haWwtNDU0My5jbGVyay5hY2NvdW50cy5kZXYk';

// Chart instances
let trendChartInstance = null;
let qualityChartInstance = null;
let financialChartInstance = null;
let commodityChartInstance = null;

// Global state
let harvestRecords = [];
let currentFilters = {
  commodity: '',
  period: 'all',
  startDate: '',
  endDate: ''
};
let currentUser = null;
let clerkLoaded = false;

const OFFLINE_QUEUE_KEY = 'agrisensa_offline_harvest_queue';

// Register Service Worker for PWA Offline capability
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      console.log('AgriSensa Service Worker registered successfully:', reg.scope);
    }).catch((err) => {
      console.warn('Service Worker registration non-fatal notice:', err);
    });
  });
}

// Init on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  initNetworkMonitoring();
  updateOfflineBanner();
  setupLiveCalculator();
  initClerkAuth();
});

// Authenticated API Fetch wrapper that includes Clerk tokens & user identity
async function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (window.Clerk && window.Clerk.session) {
    try {
      const token = await window.Clerk.session.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (e) {
      console.warn('Clerk session token notice:', e);
    }
  }
  if (window.Clerk && window.Clerk.user) {
    const user = window.Clerk.user;
    headers['X-User-Id'] = user.id;
    headers['X-User-Email'] = user.primaryEmailAddress ? user.primaryEmailAddress.emailAddress : '';
    headers['X-User-Name'] = user.fullName || user.firstName || 'Petani Terdaftar';
  }
  return headers;
}

async function apiFetch(url, options = {}) {
  if (!window.Clerk || !window.Clerk.user) {
    console.warn('apiFetch blocked: User not authenticated');
    return new Response(JSON.stringify({ success: false, message: 'Autentikasi diperlukan.' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  const authHeaders = await getAuthHeaders();
  const combinedHeaders = { ...authHeaders, ...(options.headers || {}) };
  if (options.body instanceof FormData) {
    delete combinedHeaders['Content-Type'];
  }
  const response = await fetch(url, { ...options, headers: combinedHeaders });
  if (response.status === 401) {
    if (window.Clerk && window.Clerk.signOut) {
      try {
        await window.Clerk.signOut();
      } catch (e) {
        console.warn('Sign out notice:', e);
      }
    }
    handleClerkAuthState();
  }
  return response;
}

const CLERK_APPEARANCE = {
  variables: {
    colorPrimary: '#10b981',
    colorBackground: '#070d1a',
    colorText: '#f8fafc',
    colorTextSecondary: '#94a3b8',
    colorInputBackground: '#0b1324',
    colorInputText: '#f8fafc',
    colorNeutral: '#334155',
    borderRadius: '0.75rem',
    fontFamily: "'Plus Jakarta Sans', sans-serif"
  },
  elements: {
    card: 'bg-transparent shadow-none border-0 p-0 text-slate-100',
    headerTitle: 'text-emerald-400 font-bold text-lg',
    headerSubtitle: 'text-slate-400 text-xs',
    formFieldLabel: 'text-slate-300 font-semibold text-xs',
    formFieldInput: 'bg-[#070d1a] border border-slate-700 text-slate-100 rounded-xl focus:border-emerald-500',
    formButtonPrimary: 'bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 text-slate-950 font-bold rounded-xl shadow-lg',
    footerActionLink: 'text-emerald-400 hover:text-emerald-300 font-semibold',
    dividerLine: 'bg-slate-800',
    dividerText: 'text-slate-500 text-xs',
    socialButtonsBlockButton: 'bg-slate-900 border border-slate-800 text-slate-200 hover:bg-slate-800'
  }
};

async function initClerkAuth() {
  const authGate = document.getElementById('authGateScreen');
  const mainApp = document.getElementById('mainDashboardApp');
  if (mainApp) mainApp.style.display = 'none';
  if (authGate) authGate.style.display = 'flex';

  const clerkSignInBtn = document.getElementById('clerkSignInBtn');
  const tabSignIn = document.getElementById('authTabSignInBtn');
  const tabSignUp = document.getElementById('authTabSignUpBtn');

  if (clerkSignInBtn) {
    clerkSignInBtn.addEventListener('click', () => {
      openClerkModal('signin');
    });
  }

  if (tabSignIn) {
    tabSignIn.addEventListener('click', () => switchAuthTab('signin'));
  }
  if (tabSignUp) {
    tabSignUp.addEventListener('click', () => switchAuthTab('signup'));
  }

  // Poll for Clerk global object if loaded via CDN
  let attempts = 0;
  const checkClerkInterval = setInterval(async () => {
    attempts++;
    if (window.Clerk) {
      clearInterval(checkClerkInterval);
      try {
        if (!window.Clerk.loaded) {
          await window.Clerk.load({ appearance: CLERK_APPEARANCE });
        }
        clerkLoaded = true;
        await handleClerkAuthState();

        // Listen for session/user updates (login / logout)
        window.Clerk.addListener(async (payload) => {
          console.log('Clerk session listener updated:', payload);
          await handleClerkAuthState();
        });
      } catch (err) {
        console.warn('Clerk initialization notice:', err);
        showFallbackAuth();
      }
    } else if (attempts > 50) {
      clearInterval(checkClerkInterval);
      showFallbackAuth();
    }
  }, 100);
}

function switchAuthTab(tab) {
  currentAuthTab = tab;
  const tabSignIn = document.getElementById('authTabSignInBtn');
  const tabSignUp = document.getElementById('authTabSignUpBtn');
  const container = document.getElementById('clerkSignInContainer');

  if (tab === 'signin') {
    if (tabSignIn) {
      tabSignIn.style.background = 'rgba(16, 185, 129, 0.2)';
      tabSignIn.style.color = '#34d399';
      tabSignIn.style.border = '1px solid rgba(16, 185, 129, 0.3)';
    }
    if (tabSignUp) {
      tabSignUp.style.background = 'transparent';
      tabSignUp.style.color = '#94a3b8';
      tabSignUp.style.border = 'none';
    }
    if (container && window.Clerk) {
      try {
        if (window.Clerk.unmountSignIn) window.Clerk.unmountSignIn(container);
        if (window.Clerk.unmountSignUp) window.Clerk.unmountSignUp(container);
      } catch (e) {}
      container.innerHTML = '';
      if (window.Clerk.mountSignIn) {
        window.Clerk.mountSignIn(container, { appearance: CLERK_APPEARANCE, routing: 'virtual' });
      }
    }
  } else {
    if (tabSignUp) {
      tabSignUp.style.background = 'rgba(16, 185, 129, 0.2)';
      tabSignUp.style.color = '#34d399';
      tabSignUp.style.border = '1px solid rgba(16, 185, 129, 0.3)';
    }
    if (tabSignIn) {
      tabSignIn.style.background = 'transparent';
      tabSignIn.style.color = '#94a3b8';
      tabSignIn.style.border = 'none';
    }
    if (container && window.Clerk) {
      try {
        if (window.Clerk.unmountSignIn) window.Clerk.unmountSignIn(container);
        if (window.Clerk.unmountSignUp) window.Clerk.unmountSignUp(container);
      } catch (e) {}
      container.innerHTML = '';
      if (window.Clerk.mountSignUp) {
        window.Clerk.mountSignUp(container, { appearance: CLERK_APPEARANCE, routing: 'virtual' });
      }
    }
  }
}

async function handleClerkAuthState() {
  const authGate = document.getElementById('authGateScreen');
  const mainApp = document.getElementById('mainDashboardApp');
  const userPill = document.getElementById('clerkUserPill');
  const signInBtn = document.getElementById('clerkSignInBtn');
  const userEmailSpan = document.getElementById('clerkUserEmail');
  const userBtnContainer = document.getElementById('clerkUserButton');
  const signInContainer = document.getElementById('clerkSignInContainer');
  const farmerIdInput = document.getElementById('farmer_id');

  if (window.Clerk && window.Clerk.user) {
    // 1. User is Authenticated: Unlock dashboard & sync data
    currentUser = window.Clerk.user;
    const email = currentUser.primaryEmailAddress ? currentUser.primaryEmailAddress.emailAddress : (currentUser.username || 'Pengguna');
    
    if (userEmailSpan) userEmailSpan.textContent = email;
    if (userPill) userPill.style.display = 'flex';
    if (signInBtn) signInBtn.style.display = 'none';
    if (authGate) authGate.style.display = 'none';
    if (mainApp) mainApp.style.display = 'block';

    // Auto fill default farmer ID in harvest creation form
    if (farmerIdInput) {
      farmerIdInput.value = currentUser.id;
    }

    // Mount Clerk user profile button safely
    if (userBtnContainer && window.Clerk.mountUserButton && !userBtnContainer.hasChildNodes()) {
      window.Clerk.mountUserButton(userBtnContainer);
    }

    // Sync account to database & load personal dashboard data
    try {
      await apiFetch(`${API_BASE}/auth/sync`, { method: 'POST' });
    } catch (e) {
      console.warn('User sync notice:', e);
    }
    fetchDashboardData(currentFilters);
  } else {
    // 2. User is NOT Authenticated: Lock dashboard completely & show auth portal
    currentUser = null;
    if (mainApp) mainApp.style.display = 'none';
    if (userPill) userPill.style.display = 'none';
    if (signInBtn) signInBtn.style.display = 'inline-flex';
    if (farmerIdInput) farmerIdInput.value = '';

    // Clear sensitive data from dashboard view
    harvestRecords = [];
    renderTable([]);
    updateKpiCards({
      total_records: 0,
      total_harvest_kg: 0,
      total_gross_revenue_idr: 0,
      total_net_profit_idr: 0,
      avg_productivity_kg_per_ha: 0,
      avg_marketable_yield_percent: 0,
      avg_roi_percent: 0
    });
    
    // Mount Sign In / Sign Up widget inside auth portal
    switchAuthTab(currentAuthTab);
    if (authGate) authGate.style.display = 'flex';
  }
}

function openClerkModal(tab = 'signin') {
  const authGate = document.getElementById('authGateScreen');
  if (authGate) authGate.style.display = 'flex';
  switchAuthTab(tab);
}

function showFallbackAuth() {
  const placeholder = document.getElementById('clerkLoadingPlaceholder');
  if (placeholder) {
    placeholder.innerHTML = `
      <div style="padding: 20px; text-align: center;">
        <p style="font-size: 13.5px; color: #f87171; margin-bottom: 12px; font-weight: 600;">
          ⚠️ Tidak dapat memuat Clerk Authentication Cloud
        </p>
        <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">
          Pastikan koneksi internet Anda stabil dan tidak ada pemblokir skrip aktif.
        </p>
        <button onclick="window.location.reload()" class="btn btn-primary btn-sm" style="font-size: 12px;">
          🔄 Muat Ulang Halaman
        </button>
      </div>
    `;
  }
}

function initEventListeners() {
  // Modal buttons
  document.getElementById('openIngestModalBtn').addEventListener('click', openModal);
  document.getElementById('closeModalBtn').addEventListener('click', closeModal);
  document.getElementById('refreshDataBtn').addEventListener('click', () => fetchDashboardData(currentFilters));

  // Webhook Notification Modal
  const openWebhookBtn = document.getElementById('openWebhookModalBtn');
  const closeWebhookBtn = document.getElementById('closeWebhookModalBtn');
  const webhookForm = document.getElementById('webhookConfigForm');
  const testWebhookBtn = document.getElementById('testWebhookBtn');

  if (openWebhookBtn) openWebhookBtn.addEventListener('click', openWebhookModal);
  if (closeWebhookBtn) closeWebhookBtn.addEventListener('click', closeWebhookModal);
  if (webhookForm) webhookForm.addEventListener('submit', handleSaveWebhookConfig);
  if (testWebhookBtn) testWebhookBtn.addEventListener('click', handleTestWebhook);

  // Sync button in offline banner
  const syncBtn = document.getElementById('syncNowBtn');
  if (syncBtn) {
    syncBtn.addEventListener('click', syncOfflineQueue);
  }

  // Dynamic Filter Bar controls
  const periodSelect = document.getElementById('filterPeriod');
  const customDateBox = document.getElementById('customDateBox');
  const commoditySelect = document.getElementById('filterCommodity');
  const applyBtn = document.getElementById('applyFilterBtn');
  const resetBtn = document.getElementById('resetFilterBtn');

  if (periodSelect) {
    periodSelect.addEventListener('change', (e) => {
      if (e.target.value === 'custom') {
        customDateBox.style.display = 'flex';
      } else {
        customDateBox.style.display = 'none';
        applyFilters();
      }
    });
  }

  if (commoditySelect) {
    commoditySelect.addEventListener('change', applyFilters);
  }

  if (applyBtn) {
    applyBtn.addEventListener('click', applyFilters);
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', resetFilters);
  }

  // Export CSV with active filters
  const exportBtn = document.getElementById('exportCsvBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', handleExportCsv);
  }

  // Form submit
  document.getElementById('harvestForm').addEventListener('submit', handleHarvestSubmit);

  // Search input
  document.getElementById('searchInput').addEventListener('input', (e) => {
    filterTable(e.target.value);
  });
}

function applyFilters() {
  const commodity = document.getElementById('filterCommodity').value.trim();
  const period = document.getElementById('filterPeriod').value;
  let startDate = '';
  let endDate = '';

  const now = new Date();

  if (period === '30') {
    const past = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    startDate = past.toISOString().split('T')[0];
    endDate = now.toISOString().split('T')[0];
  } else if (period === '90') {
    const past = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
    startDate = past.toISOString().split('T')[0];
    endDate = now.toISOString().split('T')[0];
  } else if (period === '365') {
    startDate = `${now.getFullYear()}-01-01`;
    endDate = `${now.getFullYear()}-12-31`;
  } else if (period === 'custom') {
    startDate = document.getElementById('filterStartDate').value;
    endDate = document.getElementById('filterEndDate').value;
  }

  currentFilters = { commodity, period, startDate, endDate };
  updateFilterSummaryBanner();
  fetchDashboardData(currentFilters);
}

function resetFilters() {
  document.getElementById('filterCommodity').value = '';
  document.getElementById('filterPeriod').value = 'all';
  document.getElementById('customDateBox').style.display = 'none';
  document.getElementById('filterStartDate').value = '';
  document.getElementById('filterEndDate').value = '';

  currentFilters = { commodity: '', period: 'all', startDate: '', endDate: '' };
  updateFilterSummaryBanner();
  fetchDashboardData({});
  showToast('Semua filter berhasil direset.', 'success');
}

function updateFilterSummaryBanner() {
  const bar = document.getElementById('filterSummaryBar');
  const text = document.getElementById('filterSummaryText');
  if (!bar || !text) return;

  const parts = [];
  if (currentFilters.commodity) {
    parts.push(`Komoditas: <strong>${currentFilters.commodity}</strong>`);
  }
  if (currentFilters.startDate || currentFilters.endDate) {
    parts.push(`Rentang: <strong>${currentFilters.startDate || 'Awal'} s/d ${currentFilters.endDate || 'Sekarang'}</strong>`);
  } else if (currentFilters.period !== 'all') {
    parts.push(`Periode: <strong>${currentFilters.period} Hari Terakhir</strong>`);
  }

  if (parts.length > 0) {
    bar.style.display = 'flex';
    text.innerHTML = `Filter Aktif: ${parts.join(' &nbsp;|&nbsp; ')}`;
  } else {
    bar.style.display = 'none';
  }
}

async function handleExportCsv() {
  const params = new URLSearchParams();
  if (currentFilters.commodity) params.append('commodity', currentFilters.commodity);
  if (currentFilters.startDate) params.append('start_date', currentFilters.startDate);
  if (currentFilters.endDate) params.append('end_date', currentFilters.endDate);
  const qs = params.toString() ? `?${params.toString()}` : '';

  try {
    showToast('⏳ Sedang menyiapkan data rekapitulasi Excel / CSV...', 'success');
    const resp = await apiFetch(`${API_BASE}/harvests/export/csv${qs}`);
    if (!resp.ok) {
      throw new Error('Gagal mengekspor data CSV');
    }
    const blob = await resp.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `rekap_panen_agrisensa_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
    showToast('✅ Berkas CSV berhasil diunduh.', 'success');
  } catch (err) {
    showToast('❌ Gagal mengunduh CSV: ' + err.message, 'error');
  }
}

// ---------------------------------------------------------------------
// 1. DATA FETCHING & DASHBOARD REFRESH
// ---------------------------------------------------------------------

async function fetchDashboardData(filterParams = {}) {
  try {
    const params = new URLSearchParams();
    if (filterParams.commodity) params.append('commodity', filterParams.commodity);
    if (filterParams.startDate) params.append('start_date', filterParams.startDate);
    if (filterParams.endDate) params.append('end_date', filterParams.endDate);
    const queryString = params.toString() ? `?${params.toString()}` : '';

    // 1. Fetch records
    const resRecords = await apiFetch(`${API_BASE}/harvests${queryString}`);
    const dataRecords = await resRecords.json();
    
    if (dataRecords.success) {
      harvestRecords = dataRecords.data.items || [];
      renderTable(harvestRecords);
      renderTrendChart(harvestRecords);
      renderQualityChart(harvestRecords);
      renderFinancialChart(harvestRecords);
      renderCommodityChart(harvestRecords);
      updateCommodityDropdown(harvestRecords);
    }

    // 2. Fetch summary KPIs
    const resSummary = await apiFetch(`${API_BASE}/analytics/summary${queryString}`);
    const dataSummary = await resSummary.json();
    if (dataSummary.success) {
      updateKpiCards(dataSummary.data);
    }

    // 3. Fetch AI Benchmark & Recommendations
    await fetchAIInsights(filterParams);

    // Update status badge safely
    const statusPill = document.getElementById('systemStatusPill');
    const statusText = document.getElementById('apiStatusText');
    const pulseDot = document.getElementById('networkPulseDot');
    if (statusPill) statusPill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    if (statusText) statusText.textContent = 'Online & Terhubung';
    if (pulseDot) pulseDot.style.backgroundColor = '#34d399';

  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    showToast('Gagal memuat data dari API. Memeriksa koneksi...', 'error');
    const statusText = document.getElementById('apiStatusText');
    if (statusText) statusText.textContent = 'API Offline';
  }
}

async function fetchAIInsights(filterParams = {}) {
  try {
    const params = new URLSearchParams();
    if (filterParams.commodity) params.append('commodity', filterParams.commodity);
    if (filterParams.startDate) params.append('start_date', filterParams.startDate);
    if (filterParams.endDate) params.append('end_date', filterParams.endDate);
    const queryString = params.toString() ? `?${params.toString()}` : '';

    const res = await apiFetch(`${API_BASE}/analytics/ai-insights${queryString}`);
    const result = await res.json();

    if (result.success && result.data) {
      updateAiInsightCard(result.data);
    }
  } catch (err) {
    console.error('Error fetching AI insights:', err);
  }
}

function updateAiInsightCard(data) {
  const statusEl = document.getElementById('aiBenchmarkStatus');
  const starsEl = document.getElementById('aiRatingStars');
  const badgeEl = document.getElementById('aiBenchmarkBadge');
  const stdProdEl = document.getElementById('aiStdProdText');
  const actualProdEl = document.getElementById('aiActualProdText');
  const deltaProdEl = document.getElementById('aiDeltaProdText');
  const lossEl = document.getElementById('aiLossText');
  const recListEl = document.getElementById('aiRecommendationList');

  if (statusEl) statusEl.textContent = data.status_label || data.status_grade || 'Optimal';
  if (starsEl) starsEl.textContent = data.rating_stars || '⭐⭐⭐⭐';
  
  if (badgeEl && data.badge_color) {
    badgeEl.style.borderColor = data.badge_color;
    badgeEl.style.backgroundColor = `${data.badge_color}22`;
  }

  if (stdProdEl) {
    stdProdEl.textContent = data.benchmark_productivity_kg_ha 
      ? `${data.benchmark_productivity_kg_ha.toLocaleString('id-ID')} kg/ha` 
      : '-';
  }

  if (actualProdEl) {
    actualProdEl.textContent = data.actual_productivity_kg_ha 
      ? `${data.actual_productivity_kg_ha.toLocaleString('id-ID')} kg/ha` 
      : '-';
  }

  if (deltaProdEl) {
    const delta = data.productivity_delta_percent || 0;
    const sign = delta > 0 ? '+' : '';
    deltaProdEl.textContent = `${sign}${delta.toFixed(1)}% vs Acuan`;
    deltaProdEl.style.color = delta >= 0 ? 'var(--emerald-400)' : '#f43f5e';
  }

  if (lossEl) {
    const loss = data.actual_loss_rate_percent || 0;
    const maxLoss = data.max_safe_loss_rate_percent || 10;
    lossEl.textContent = `${loss.toFixed(1)}% (Maks ${maxLoss}%)`;
    lossEl.style.color = loss <= maxLoss ? 'var(--emerald-400)' : '#f43f5e';
  }

  if (recListEl) {
    const list = data.recommendations || data.insights || [];
    if (list.length === 0) {
      recListEl.innerHTML = `<li>Semua parameter budidaya berada dalam rentang standar optimal.</li>`;
    } else {
      recListEl.innerHTML = list.map(item => `<li>${item}</li>`).join('');
    }
  }
}

function updateCommodityDropdown(records) {
  const select = document.getElementById('filterCommodity');
  if (!select) return;

  const currentVal = select.value;
  const existingOptions = Array.from(select.options).map(o => o.value);

  records.forEach(r => {
    if (r.commodity && !existingOptions.includes(r.commodity)) {
      const opt = document.createElement('option');
      opt.value = r.commodity;
      opt.textContent = `🌱 ${r.commodity}`;
      select.appendChild(opt);
    }
  });

  select.value = currentVal;
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
    const statusClass = `status-${r.status.toLowerCase()}`;

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
          <select class="status-selector-pill ${statusClass}" onchange="updateHarvestStatus('${r.harvest_id}', this.value)" title="Klik untuk mengubah alur status data panen">
            <option value="validated" ${r.status === 'validated' ? 'selected' : ''}>🔵 VALIDATED</option>
            <option value="approved" ${r.status === 'approved' ? 'selected' : ''}>🟢 APPROVED</option>
            <option value="needs_review" ${r.status === 'needs_review' ? 'selected' : ''}>🟠 REVIEW</option>
            <option value="draft" ${r.status === 'draft' ? 'selected' : ''}>⚪ DRAFT</option>
          </select>
        </td>
        <td>
          <div style="display: flex; gap: 6px; align-items: center;">
            ${r.status !== 'approved' ? `
              <button class="btn btn-primary btn-sm btn-approve-quick" onclick="updateHarvestStatus('${r.harvest_id}', 'approved')" title="Setujui data panen ini secara resmi">
                ✓ Setujui
              </button>
            ` : ''}
            <button class="btn btn-primary btn-sm" onclick="openPdfReport('${r.harvest_id}')" title="Cetak / Simpan Laporan PDF">
              📄 PDF
            </button>
            <button class="btn btn-secondary btn-sm" onclick="viewDetail('${r.harvest_id}')" title="Lihat Detail Lengkap">
              👁️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function updateHarvestStatus(harvestId, newStatus) {
  try {
    showToast(`⏳ Memperbarui status panen menjadi "${newStatus.toUpperCase()}"...`, 'success');
    const res = await apiFetch(`${API_BASE}/harvests/${harvestId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    const result = await res.json();
    if (res.ok && result.success) {
      showToast(`✅ Status panen ${harvestId.substring(0, 8)} berhasil diubah ke "${newStatus.toUpperCase()}"!`, 'success');
      fetchDashboardData(currentFilters);
    } else {
      showToast(result.detail || result.message || 'Gagal mengubah status panen.', 'error');
    }
  } catch (err) {
    showToast('Terjadi kesalahan koneksi saat mengubah status.', 'error');
  }
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
// OFFLINE PWA & LOCAL STORAGE QUEUE SYNC
// ---------------------------------------------------------------------

function initNetworkMonitoring() {
  window.addEventListener('online', () => {
    updateOfflineBanner();
    showToast('🌐 Koneksi internet terhubung kembali! Sinkronisasi otomatis...', 'success');
    syncOfflineQueue();
  });

  window.addEventListener('offline', () => {
    updateOfflineBanner();
    showToast('📡 Anda masuk ke Mode Offline. Data panen akan disimpan secara lokal.', 'error');
  });
}

function getOfflineQueue() {
  try {
    const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveToOfflineQueue(item) {
  const queue = getOfflineQueue();
  queue.push({
    ...item,
    queued_at: new Date().toISOString()
  });
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
  updateOfflineBanner();
}

function updateOfflineBanner() {
  const queue = getOfflineQueue();
  const banner = document.getElementById('offlineSyncBanner');
  const countEl = document.getElementById('offlineQueueCount');
  const isOnline = navigator.onLine;

  if (countEl) countEl.textContent = queue.length;

  if (banner) {
    if (!isOnline || queue.length > 0) {
      banner.style.display = 'flex';
      const titleEl = document.getElementById('offlineBannerTitle');
      const textEl = document.getElementById('offlineStatusText');
      if (!isOnline) {
        if (titleEl) titleEl.textContent = '📡 Mode Offline (Di Lahan / Tanpa Sinyal)';
        if (textEl) textEl.textContent = `Koneksi internet terputus. ${queue.length} data panen tersimpan di memori lokal perangkat.`;
      } else {
        if (titleEl) titleEl.textContent = '🔄 Data Siap Disinkronkan ke Cloud';
        if (textEl) textEl.textContent = `${queue.length} data panen tersimpan offline siap diunggah ke database server.`;
      }
    } else {
      banner.style.display = 'none';
    }
  }

  // Update Network Status Badge
  const netText = document.getElementById('networkStatusText');
  const netDot = document.getElementById('networkPulseDot');

  if (netText && netDot) {
    if (isOnline) {
      netText.textContent = 'Online';
      netDot.style.backgroundColor = 'var(--emerald-400)';
    } else {
      netText.textContent = 'Offline';
      netDot.style.backgroundColor = '#f59e0b';
    }
  }
}

async function syncOfflineQueue() {
  const queue = getOfflineQueue();
  if (queue.length === 0) {
    showToast('Tidak ada data panen di antrean offline.', 'success');
    updateOfflineBanner();
    return;
  }

  if (!navigator.onLine) {
    showToast('Perangkat masih dalam kondisi offline. Sinkronisasi ditunda.', 'error');
    return;
  }

  showToast(`⏳ Mulai menyinkronkan ${queue.length} data panen ke cloud...`, 'success');
  let successCount = 0;
  const remainingQueue = [];

  for (const item of queue) {
    try {
      const res = await apiFetch(`${API_BASE}/harvests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        successCount++;
      } else {
        remainingQueue.push(item);
      }
    } catch (err) {
      remainingQueue.push(item);
    }
  }

  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(remainingQueue));
  updateOfflineBanner();

  if (successCount > 0) {
    showToast(`✅ Berhasil mengunggah ${successCount} data panen ke cloud database!`, 'success');
    fetchDashboardData(currentFilters);
  }

  if (remainingQueue.length > 0) {
    showToast(`⚠️ ${remainingQueue.length} data panen masih belum terunggah.`, 'error');
  }
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

  // If currently offline, immediately save to offline queue
  if (!navigator.onLine) {
    saveToOfflineQueue(payload);
    showToast(`📥 Tersimpan Offline: Data panen ${payload.commodity} diamankan di memori lokal perangkat. Akan otomatis terunggah saat online!`, 'success');
    closeModal();
    return;
  }

  try {
    const res = await apiFetch(`${API_BASE}/harvests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();
    if (res.ok && result.success) {
      showToast(`Data panen ${payload.commodity} berhasil disimpan dan tervalidasi!`, 'success');
      closeModal();
      fetchDashboardData(currentFilters);
    } else {
      showToast(result.detail || result.message || 'Gagal menyimpan data panen', 'error');
    }
  } catch (err) {
    console.warn('Network error during save, falling back to offline queue:', err);
    saveToOfflineQueue(payload);
    showToast(`📥 Terjadi kendala sinyal. Data panen ${payload.commodity} disimpan ke antrean offline lokal!`, 'success');
    closeModal();
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
// 7. ACTIONS & HELPERS
// ---------------------------------------------------------------------

function openPdfReport(harvestId) {
  const reportUrl = `${API_BASE}/harvests/${harvestId}/report`;
  window.open(reportUrl, '_blank');
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

async function openWebhookModal() {
  document.getElementById('webhookModal').classList.add('active');
  try {
    const res = await apiFetch(`${API_BASE}/config/notifications`);
    const data = await res.json();
    if (data.success && data.data) {
      document.getElementById('webhookUrlInput').value = data.data.raw_webhook_url || '';
      document.getElementById('webhookEnabledToggle').checked = data.data.is_enabled !== false;
    }
  } catch (err) {
    console.error('Failed to load webhook config:', err);
  }
}

function closeWebhookModal() {
  document.getElementById('webhookModal').classList.remove('active');
}

async function handleSaveWebhookConfig(e) {
  e.preventDefault();
  const webhookUrl = document.getElementById('webhookUrlInput').value.trim();
  const isEnabled = document.getElementById('webhookEnabledToggle').checked;

  try {
    const res = await apiFetch(`${API_BASE}/config/notifications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url: webhookUrl, is_enabled: isEnabled })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Konfigurasi notifikasi WhatsApp / Webhook berhasil disimpan!', 'success');
      closeWebhookModal();
    } else {
      showToast(data.detail || 'Gagal menyimpan konfigurasi.', 'error');
    }
  } catch (err) {
    showToast('Terjadi kesalahan saat menyimpan webhook.', 'error');
  }
}

async function handleTestWebhook() {
  const webhookUrl = document.getElementById('webhookUrlInput').value.trim();
  if (!webhookUrl) {
    showToast('Harap masukkan URL Webhook terlebih dahulu sebelum menguji.', 'error');
    return;
  }

  showToast('⏳ Mengirim pesan uji coba ke webhook...', 'success');

  try {
    const res = await apiFetch(`${API_BASE}/config/notifications/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url: webhookUrl })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('✅ Pesan uji coba BERHASIL terkirim ke Webhook!', 'success');
    } else {
      showToast(data.detail || data.message || 'Uji coba gagal terkirim.', 'error');
    }
  } catch (err) {
    showToast('Gagal mengirim uji coba webhook: ' + err.message, 'error');
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



