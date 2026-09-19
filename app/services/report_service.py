from datetime import datetime
from app.schemas.harvest import HarvestRecordResponse
from app.services.ai_insight_service import ai_insight_service


class ReportService:
    """Service untuk membuat dokumen laporan panen resmi (format Cetak / Simpan PDF)."""

    def generate_printable_html(self, record: HarvestRecordResponse) -> str:
        kpi = record.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None
        ai_eval = ai_insight_service.evaluate_harvest_record(record)

        grades_rows = ""
        if record.quality_grades and len(record.quality_grades) > 0:
            for g in record.quality_grades:
                grades_rows += f"""
                <tr>
                  <td><strong>Grade {g.grade}</strong></td>
                  <td>{g.quantity_kg:,.1f} kg</td>
                  <td>Rp {g.price_per_kg:,.0f}</td>
                  <td>Rp {g.quantity_kg * g.price_per_kg:,.0f}</td>
                  <td>{g.notes or '-'}</td>
                </tr>
                """
        else:
            marketable_rev = record.marketable_quantity_kg * record.selling_price_per_kg
            grades_rows = f"""
            <tr>
              <td><strong>Grade Layak Jual (Marketable)</strong></td>
              <td>{record.marketable_quantity_kg:,.1f} kg</td>
              <td>Rp {record.selling_price_per_kg:,.0f}</td>
              <td>Rp {marketable_rev:,.0f}</td>
              <td>Mutu standar konsumsi / pasar</td>
            </tr>
            <tr>
              <td><strong>Grade Afkir / Rusak (Loss)</strong></td>
              <td>{record.damaged_quantity_kg:,.1f} kg</td>
              <td>Rp 0</td>
              <td>Rp 0</td>
              <td>Tidak layak jual ({record.damage_cause or 'Sortasi Lapangan'})</td>
            </tr>
            """

        productivity_val = f"{prod_kpi.productivity_kg_per_ha:,.1f}" if prod_kpi else "-"
        roi_val = f"{econ_kpi.roi_percent:.2f}%" if econ_kpi else "-"
        bep_val = f"Rp {econ_kpi.break_even_price_idr:,.0f}" if econ_kpi else "-"
        loss_val = f"{prod_kpi.loss_rate_percent:.2f}%" if prod_kpi else "-"

        return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Laporan Panen - {record.commodity} - {record.farm_id}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@600;700;800&display=swap');
    
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #0f172a;
      color: #1e293b;
      padding: 24px;
      line-height: 1.5;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    /* Action bar at top (hidden on print) */
    .action-bar {{
      max-width: 880px;
      margin: 0 auto 20px auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #1e293b;
      padding: 14px 22px;
      border-radius: 12px;
      border: 1px solid #334155;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    .action-btn {{
      background: linear-gradient(135deg, #10b981, #059669);
      color: #ffffff;
      border: none;
      padding: 10px 22px;
      font-weight: 700;
      border-radius: 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13.5px;
      text-decoration: none;
      transition: all 0.2s;
      box-shadow: 0 2px 10px rgba(16, 185, 129, 0.4);
    }}
    .action-btn:hover {{
      background: linear-gradient(135deg, #34d399, #10b981);
      transform: translateY(-1px);
    }}
    .action-btn-sec {{
      background: #334155;
      color: #f1f5f9;
      border: 1px solid #475569;
      box-shadow: none;
    }}
    .action-btn-sec:hover {{ background: #475569; }}

    /* Document page */
    .document-page {{
      max-width: 880px;
      margin: 0 auto;
      background: #ffffff;
      padding: 38px 46px;
      border-radius: 12px;
      box-shadow: 0 10px 35px rgba(0,0,0,0.3);
    }}

    /* =========================================================
       KOP SURAT RESMI (OFFICIAL LETTERHEAD)
       ========================================================= */
    .kop-container {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
      padding-bottom: 14px;
    }}

    .kop-brand-wrap {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .kop-logo-box {{
      width: 58px;
      height: 58px;
      border-radius: 12px;
      background: linear-gradient(135deg, #059669, #0d9488);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 30px;
      color: #ffffff;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
    }}

    .kop-brand-text h1 {{
      font-family: 'Outfit', sans-serif;
      font-size: 19px;
      font-weight: 800;
      color: #065f46;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      line-height: 1.2;
    }}

    .kop-brand-text .kop-sub1 {{
      font-size: 11px;
      font-weight: 700;
      color: #047857;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-top: 2px;
    }}

    .kop-brand-text .kop-sub2 {{
      font-size: 10.5px;
      color: #64748b;
      margin-top: 2px;
      line-height: 1.35;
    }}

    .kop-meta-box {{
      text-align: right;
      font-size: 11px;
      color: #334155;
      border-left: 2px solid #e2e8f0;
      padding-left: 16px;
      flex-shrink: 0;
      line-height: 1.5;
    }}

    .kop-badge {{
      display: inline-block;
      padding: 3px 9px;
      background: #ecfdf5;
      color: #047857;
      font-weight: 700;
      border-radius: 6px;
      font-size: 10.5px;
      text-transform: uppercase;
      border: 1px solid #a7f3d0;
      margin-bottom: 4px;
    }}

    /* Double line border for official letterhead */
    .kop-double-divider {{
      border-top: 3px solid #047857;
      border-bottom: 1px solid #10b981;
      height: 3px;
      margin-bottom: 22px;
    }}

    /* Document Title Banner */
    .doc-title-banner {{
      text-align: center;
      margin-bottom: 20px;
    }}
    .doc-title-banner h2 {{
      font-family: 'Outfit', sans-serif;
      font-size: 15px;
      font-weight: 800;
      color: #0f172a;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .doc-title-banner p {{
      font-size: 11.5px;
      color: #64748b;
      margin-top: 2px;
    }}

    /* KPI Highlights Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 22px;
    }}
    .kpi-card {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px 14px;
      text-align: center;
    }}
    .kpi-card.highlight {{
      background: #f0fdf4;
      border-color: #bbf7d0;
    }}
    .kpi-card.highlight .kpi-val {{
      color: #059669;
    }}
    .kpi-val {{
      font-size: 17px;
      font-weight: 800;
      color: #0f172a;
    }}
    .kpi-label {{
      font-size: 10px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-top: 3px;
    }}

    /* Section Headings */
    h3 {{
      font-size: 12.5px;
      font-weight: 700;
      color: #0f172a;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
      padding-bottom: 4px;
      border-bottom: 1.5px solid #e2e8f0;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    /* Tables */
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 18px;
      font-size: 11.5px;
    }}
    .data-table th, .data-table td {{
      padding: 7px 11px;
      border: 1px solid #e2e8f0;
      text-align: left;
    }}
    .data-table th {{
      background: #f1f5f9;
      color: #334155;
      font-weight: 600;
    }}
    .data-table td.money {{
      font-family: 'Plus Jakarta Sans', monospace;
      font-size: 11.5px;
    }}

    .summary-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 18px;
    }}

    .footer {{
      margin-top: 24px;
      padding-top: 12px;
      border-top: 1px solid #e2e8f0;
      font-size: 10px;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    /* Print Stylesheet (Clean A4 PDF formatting) */
    @media print {{
      body {{
        background: #ffffff !important;
        padding: 0 !important;
      }}
      .action-bar {{
        display: none !important;
      }}
      .document-page {{
        box-shadow: none !important;
        padding: 0 !important;
        max-width: 100% !important;
      }}
      .kpi-card, .data-table, .summary-box, .kop-container {{
        page-break-inside: avoid;
      }}
      @page {{
        size: A4 portrait;
        margin: 10mm 14mm;
      }}
    }}
  </style>
</head>
<body>

  <!-- Top Action Bar -->
  <div class="action-bar">
    <div style="color: #94a3b8; font-size: 13px;">
      📄 <strong>Laporan Resmi Rekapitulasi Panen</strong> — Siap Cetak / Simpan sebagai PDF Resmi
    </div>
    <div style="display: flex; gap: 10px;">
      <button class="action-btn" onclick="window.print()">
        🖨️ Cetak / Simpan PDF
      </button>
      <button class="action-btn action-btn-sec" onclick="window.close()">
        ✕ Tutup
      </button>
    </div>
  </div>

  <!-- Document Page -->
  <div class="document-page">
    
    <!-- KOP SURAT RESMI AGRISENSA HARVEST INTELLIGENCE -->
    <div class="kop-container">
      <div class="kop-brand-wrap">
        <div class="kop-logo-box">🌾</div>
        <div class="kop-brand-text">
          <h1>AGRISENSA HARVEST INTELLIGENCE</h1>
          <div class="kop-sub1">Sistem Cerdas Pencatatan & Analitik Rekapitulasi Panen</div>
          <div class="kop-sub2">
            Standar Acuan Agribisnis Nasional (Kementerian Pertanian & BPS RI)<br>
            Portal Digital: <em>agrisensa-harvest-api-production.up.railway.app</em>
          </div>
        </div>
      </div>

      <div class="kop-meta-box">
        <div><span class="kop-badge">{record.status.upper()}</span></div>
        <div><strong>No:</strong> <code>HARV-{record.harvest_id[:8].upper()}</code></div>
        <div><strong>Tgl Cetak:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')} WIB</div>
        <div><strong>ID Kebun:</strong> {record.farm_id}</div>
      </div>
    </div>

    <!-- Double Border Divider -->
    <div class="kop-double-divider"></div>

    <!-- Judul Dokumen -->
    <div class="doc-title-banner">
      <h2>LEMBAR LAPORAN REKAPITULASI & EVALUASI PANEN</h2>
      <p>Komoditas: <strong>{record.commodity}</strong> (Varietas: {record.variety or 'Standar'}) &bull; Periode Panen: {record.harvest_date}</p>
    </div>

    <!-- KPI Summary Grid -->
    <div class="kpi-grid">
      <div class="kpi-card highlight">
        <div class="kpi-val">{record.harvest_quantity_kg:,.0f} kg</div>
        <div class="kpi-label">Total Hasil Panen</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{productivity_val} <span style="font-size:11px; font-weight:normal;">kg/ha</span></div>
        <div class="kpi-label">Produktivitas</div>
      </div>
      <div class="kpi-card highlight">
        <div class="kpi-val">Rp {record.net_profit:,.0f}</div>
        <div class="kpi-label">Laba Bersih</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-val">{roi_val}</div>
        <div class="kpi-label">Return on Investment (ROI)</div>
      </div>
    </div>

    <!-- 1. Detail Kebun & Panen -->
    <h3>📋 Identitas Kebun & Budidaya</h3>
    <table class="data-table">
      <tr>
        <th width="25%">Komoditas / Varietas</th>
        <td width="35%"><strong>{record.commodity}</strong> ({record.variety or 'Varietas Standar'})</td>
        <th width="20%">Luas Lahan</th>
        <td width="20%">{record.land_area_ha} ha ({record.original_land_area} {record.original_land_area_unit})</td>
      </tr>
      <tr>
        <th>ID Kebun / ID Petani</th>
        <td><code>{record.farm_id}</code> / <code>{record.farmer_id}</code></td>
        <th>Panen Ke</th>
        <td>Ke-{record.harvest_sequence}</td>
      </tr>
      <tr>
        <th>Periode Budidaya</th>
        <td>Tanam: {record.planting_date} &nbsp;→&nbsp; Panen: {record.harvest_date}</td>
        <th>Kanal Penjualan</th>
        <td>{record.sales_channel or 'Pasar Umum / Tengkulak'}</td>
      </tr>
    </table>

    <!-- 2. Analisis Finansial & Produksi -->
    <h3>💰 Kinerja Finansial & Mutu Hasil</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Komponen</th>
          <th>Kuantitas / Nilai</th>
          <th>Satuan / Rata-rata</th>
          <th>Catatan Evaluasi</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Total Hasil Panen</strong></td>
          <td><strong>{record.harvest_quantity_kg:,.1f} kg</strong></td>
          <td>100%</td>
          <td>Volume kotor seluruh panen</td>
        </tr>
        <tr>
          <td>Hasil Layak Jual (Marketable)</td>
          <td>{record.marketable_quantity_kg:,.1f} kg</td>
          <td>{((record.marketable_quantity_kg / record.harvest_quantity_kg) * 100) if record.harvest_quantity_kg else 0:.1f}%</td>
          <td>Memenuhi standar mutu pasar</td>
        </tr>
        <tr>
          <td>Hasil Rusak / Afkir (Damaged)</td>
          <td>{record.damaged_quantity_kg:,.1f} kg</td>
          <td>Loss Rate: {loss_val}</td>
          <td>{record.damage_cause or 'Kerusakan fisik / hama wajar'}</td>
        </tr>
        <tr style="background: #f8fafc;">
          <td><strong>Pendapatan Kotor (Omset)</strong></td>
          <td class="money" style="color: #059669;"><strong>Rp {record.gross_revenue:,.0f}</strong></td>
          <td>Rp {record.selling_price_per_kg:,.0f} / kg</td>
          <td>Total penerimaan penjualan</td>
        </tr>
        <tr style="background: #f8fafc;">
          <td><strong>Total Biaya Produksi</strong></td>
          <td class="money" style="color: #dc2626;"><strong>Rp {record.total_production_cost:,.0f}</strong></td>
          <td>Rp {(record.total_production_cost / record.harvest_quantity_kg) if record.harvest_quantity_kg else 0:,.0f} / kg</td>
          <td>Biaya input, tenaga kerja, operasional</td>
        </tr>
        <tr style="background: #ecfdf5;">
          <td><strong>Keuntungan Bersih (Net Profit)</strong></td>
          <td class="money" style="color: #047857; font-size: 14px;"><strong>Rp {record.net_profit:,.0f}</strong></td>
          <td>BEP: {bep_val} / kg</td>
          <td>Margin laba bersih tercapai</td>
        </tr>
      </tbody>
    </table>

    <!-- 3. Rincian Mutu / Grade -->
    <h3>🎯 Rincian Mutu & Grading</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Grade / Klasifikasi</th>
          <th>Kuantitas (kg)</th>
          <th>Harga Satuan (IDR/kg)</th>
          <th>Subtotal Penjualan (IDR)</th>
          <th>Keterangan Mutu</th>
        </tr>
      </thead>
      <tbody>
        {grades_rows}
      </tbody>
    </table>

    <!-- 4. Evaluasi Kinerja AI & Benchmark Nasional -->
    <h3>🤖 Evaluasi Cerdas AI & Benchmark Nasional (Kementan/BPS)</h3>
    <div class="summary-box" style="background: #f0fdf4; border-color: #bbf7d0; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <div>
          <span style="font-size: 13px; font-weight: 700; color: #166534;">Status Evaluasi: {ai_eval['status_label']}</span>
          <span style="margin-left: 8px;">{ai_eval['rating_stars']}</span>
        </div>
        <div style="font-size: 11px; font-weight: 700; color: #15803d; background: #dcfce7; padding: 3px 8px; border-radius: 6px;">
          Grade: {ai_eval['status_grade']}
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px; font-size: 11px;">
        <div style="background: #ffffff; padding: 7px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
          <span style="color: #64748b; display: block;">Standar Acuan:</span>
          <strong>{ai_eval['benchmark_productivity_kg_ha']:,.0f} kg/ha</strong>
        </div>
        <div style="background: #ffffff; padding: 7px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
          <span style="color: #64748b; display: block;">Deviasi Produktivitas:</span>
          <strong style="color: {'#16a34a' if ai_eval['productivity_delta_percent'] >= 0 else '#dc2626'};">
            {'+' if ai_eval['productivity_delta_percent'] > 0 else ''}{ai_eval['productivity_delta_percent']:.1f}% vs Standar
          </strong>
        </div>
        <div style="background: #ffffff; padding: 7px 10px; border-radius: 6px; border: 1px solid #dcfce7;">
          <span style="color: #64748b; display: block;">Loss Rate (Toleransi {ai_eval['max_safe_loss_rate_percent']}%):</span>
          <strong style="color: {'#16a34a' if ai_eval['actual_loss_rate_percent'] <= ai_eval['max_safe_loss_rate_percent'] else '#dc2626'};">
            {ai_eval['actual_loss_rate_percent']:.1f}%
          </strong>
        </div>
      </div>

      <div style="border-top: 1px dashed #86efac; padding-top: 8px;">
        <strong style="font-size: 11px; color: #166534; display: block; margin-bottom: 4px;">Rekomendasi Cerdas Agronomi & Pasca Panen:</strong>
        <ul style="margin-left: 18px; font-size: 11px; color: #334155; line-height: 1.5;">
          {''.join(f'<li>{rec}</li>' for rec in ai_eval['recommendations'])}
        </ul>
      </div>
    </div>

    <!-- Footer -->
    <div class="footer">
      <div>
        ID Panen: <code>{record.harvest_id}</code> &bull; Sistem AgriSensa AI Engine v1.0
      </div>
      <div>
        Dicetak secara resmi dari <strong>AgriSensa Harvest Intelligence</strong>
      </div>
    </div>

  </div>

</body>
</html>"""


report_service = ReportService()
