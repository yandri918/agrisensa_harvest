from typing import Dict, Any, Optional, List
from datetime import datetime

# Standar Benchmark Komoditas Pertanian Nasional (Acuan BPS & Balitbangtan / Kementan RI)
BENCHMARKS = {
    "Cabai Merah": {
        "standard_productivity_kg_ha": 6000.0,
        "max_loss_rate_pct": 10.0,
        "standard_roi_pct": 50.0,
        "optimal_price_idr_kg": 35000.0,
        "category": "Hortikultura"
    },
    "Padi Sawah": {
        "standard_productivity_kg_ha": 5800.0,
        "max_loss_rate_pct": 5.0,
        "standard_roi_pct": 40.0,
        "optimal_price_idr_kg": 6500.0,
        "category": "Pangan"
    },
    "Jagung Pipil": {
        "standard_productivity_kg_ha": 6500.0,
        "max_loss_rate_pct": 6.0,
        "standard_roi_pct": 45.0,
        "optimal_price_idr_kg": 5000.0,
        "category": "Pangan"
    },
    "Bawang Merah": {
        "standard_productivity_kg_ha": 8500.0,
        "max_loss_rate_pct": 8.0,
        "standard_roi_pct": 55.0,
        "optimal_price_idr_kg": 25000.0,
        "category": "Hortikultura"
    },
    "Tomat": {
        "standard_productivity_kg_ha": 16000.0,
        "max_loss_rate_pct": 12.0,
        "standard_roi_pct": 45.0,
        "optimal_price_idr_kg": 12000.0,
        "category": "Hortikultura"
    }
}

DEFAULT_BENCHMARK = {
    "standard_productivity_kg_ha": 5500.0,
    "max_loss_rate_pct": 8.0,
    "standard_roi_pct": 40.0,
    "optimal_price_idr_kg": 15000.0,
    "category": "Umum"
}


class AIInsightService:
    """Service untuk komparasi benchmark produktivitas, deviasi kinerja, analisis susut/kerusakan, dan rekomendasi agronomi berbasis data matematis."""

    def evaluate_harvest_record(self, record: Any) -> Dict[str, Any]:
        commodity = record.commodity
        benchmark = BENCHMARKS.get(commodity, DEFAULT_BENCHMARK)
        std_prod = benchmark["standard_productivity_kg_ha"]
        max_loss = benchmark["max_loss_rate_pct"]

        kpi = record.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None

        # 1. Kalkulasi Produktivitas Riil (kg/ha)
        actual_prod = prod_kpi.productivity_kg_per_ha if prod_kpi else ((record.harvest_quantity_kg / record.land_area_ha) if record.land_area_ha > 0 else 0)
        
        # 2. Kalkulasi Deviasi Kinerja Produktivitas vs Benchmark
        prod_delta_pct = ((actual_prod - std_prod) / std_prod * 100) if std_prod > 0 else 0

        # 3. Kalkulasi Tingkat Kerusakan Fisik / Susut Pasca Panen Riil (%)
        actual_loss = prod_kpi.loss_rate_percent if prod_kpi else ((record.damaged_quantity_kg / record.harvest_quantity_kg * 100) if record.harvest_quantity_kg > 0 else 0)
        loss_delta_pct = actual_loss - max_loss  # Positif berarti melebihi ambang batas toleransi

        # 4. Kalkulasi Keekonomian & ROI (%)
        actual_roi = econ_kpi.roi_percent if econ_kpi else (((record.net_profit / record.total_production_cost) * 100) if record.total_production_cost > 0 else 0)
        gross_rev = record.gross_revenue
        tot_cost = record.total_production_cost
        rc_ratio = (gross_rev / tot_cost) if tot_cost > 0 else 1.0

        # 5. Multi-Criteria Scoring Index (Skor 0 - 100)
        # Bobot: Produktivitas (40%), Mutu / Susut (35%), Finansial / ROI (25%)
        prod_score = min(100.0, max(0.0, 50.0 + (prod_delta_pct * 1.5)))
        loss_score = min(100.0, max(0.0, 100.0 - (actual_loss / max_loss * 50.0)))
        roi_score = min(100.0, max(0.0, 50.0 + ((actual_roi - 40.0) * 1.0)))

        composite_score = (prod_score * 0.40) + (loss_score * 0.35) + (roi_score * 0.25)

        # Penentuan Grade Status & Bintang Berdasarkan Skor Komposit
        if composite_score >= 82.0 and loss_delta_pct <= 0:
            status_grade = "SUPERIOR"
            status_label = "Sangat Unggul & Efisien"
            badge_color = "#10b981"
            rating_stars = "⭐⭐⭐⭐⭐"
        elif composite_score >= 68.0 and loss_delta_pct <= 3.0:
            status_grade = "OPTIMAL"
            status_label = "Optimal & Sesuai Standar"
            badge_color = "#06b6d4"
            rating_stars = "⭐⭐⭐⭐"
        elif composite_score >= 50.0:
            status_grade = "MODERATE"
            status_label = "Cukup (Perlu Optimasi Minor)"
            badge_color = "#f59e0b"
            rating_stars = "⭐⭐⭐"
        else:
            status_grade = "NEEDS_IMPROVEMENT"
            status_label = "Di Bawah Potensi Maksimal"
            badge_color = "#f43f5e"
            rating_stars = "⭐⭐"

        # 6. Rekomendasi Cerdas Dinamis Berbasis Data Riil
        recommendations = []

        # Analisis Deviasi Kinerja
        if prod_delta_pct >= 20.0:
            recommendations.append(f"🏆 Produktivitas istimewa (+{prod_delta_pct:.1f}% di atas standar {std_prod:,.0f} kg/ha). Formula pemupukan dan manajemen irigasi lahan ini sangat efektif.")
        elif prod_delta_pct >= 5.0:
            recommendations.append(f"📈 Produktivitas melampaui target nasional (+{prod_delta_pct:.1f}% vs standar acuan {std_prod:,.0f} kg/ha).")
        elif prod_delta_pct >= -5.0:
            recommendations.append(f"✅ Produktivitas berjalan stabil dan selaras dengan standar acuan {commodity} ({std_prod:,.0f} kg/ha).")
        elif prod_delta_pct >= -20.0:
            recommendations.append(f"⚠️ Produktivitas berada {abs(prod_delta_pct):.1f}% di bawah potensi ({std_prod:,.0f} kg/ha). Evaluasi jarak tanam (populasi populasi per ha) dan pemupukan fase vegetatif.")
        else:
            recommendations.append(f"🚨 Terjadi defisit produktivitas signifikan ({abs(prod_delta_pct):.1f}% di bawah standar acuan {std_prod:,.0f} kg/ha). Lakukan uji kesuburan hara tanah (N-P-K & pH) serta tinjau drainase lahan.")

        # Analisis Tingkat Kerusakan & Gejala Hama Riil
        if loss_delta_pct > 0:
            pests_info = []
            if record.pest_disease:
                for p in record.pest_disease:
                    p_name = p.name if hasattr(p, 'name') else p.get('name', '')
                    p_sev = p.severity_percent if hasattr(p, 'severity_percent') else p.get('severity_percent', 0)
                    if p_name:
                        pests_info.append(f"{p_name} ({p_sev}% serangan)")
            
            pest_suffix = f" terindikasi akibat {', '.join(pests_info)}" if pests_info else ""
            damage_cause_suffix = f" (Faktor: {record.damage_cause})" if record.damage_cause else ""
            
            recommendations.append(
                f"🔍 Tingkat kerusakan {actual_loss:.1f}% melampaui ambang batas toleransi ({max_loss:.1f}%){pest_suffix}{damage_cause_suffix}. Disarankan rotasi fungisida/insektisida terpadu dan perbaikan teknik sortasi saat pemetikan."
            )
        else:
            recommendations.append(
                f"✨ Mutu hasil panen terjaga prima dengan tingkat susut rendah ({actual_loss:.1f}% vs batas toleransi {max_loss:.1f}%)."
            )

        # Analisis Finansial & Kelayakan Usaha
        if rc_ratio >= 1.5:
            recommendations.append(f"💰 Efisiensi ekonomi sangat menguntungkan (R/C Ratio {rc_ratio:.2f}, ROI {actual_roi:.1f}%). Usaha tani ini memiliki ketahanan harga pasar yang kuat.")
        elif rc_ratio >= 1.2:
            recommendations.append(f"💵 Kelayakan finansial sehat (R/C Ratio {rc_ratio:.2f}, ROI {actual_roi:.1f}%).")
        else:
            recommendations.append(f"💡 Margin tipis (R/C Ratio {rc_ratio:.2f}, ROI {actual_roi:.1f}%). Tingkatkan efisiensi pembelian input sarana produksi dan pertimbangkan penjualan langsung ke mitra industri/offtaker.")

        return {
            "commodity": commodity,
            "status_grade": status_grade,
            "status_label": status_label,
            "badge_color": badge_color,
            "rating_stars": rating_stars,
            "composite_score": round(composite_score, 1),
            "benchmark_productivity_kg_ha": std_prod,
            "actual_productivity_kg_ha": round(actual_prod, 1),
            "productivity_delta_percent": round(prod_delta_pct, 1),
            "max_safe_loss_rate_percent": max_loss,
            "actual_loss_rate_percent": round(actual_loss, 1),
            "loss_delta_percent": round(loss_delta_pct, 1),
            "rc_ratio": round(rc_ratio, 2),
            "actual_roi_percent": round(actual_roi, 1),
            "recommendations": recommendations,
            "insights": recommendations
        }

    def evaluate_records_collection(self, records: List[Any], commodity_filter: Optional[str] = None) -> Dict[str, Any]:
        """Menghitung evaluasi benchmark AI agregat berbasis kalkulasi statistik multi-komoditas riil."""
        if not records:
            return {
                "target": "Tidak Ada Data",
                "status_grade": "NO_DATA",
                "status_label": "Belum Ada Data Panen",
                "badge_color": "#64748b",
                "rating_stars": "☆☆☆☆☆",
                "benchmark_productivity_kg_ha": 0,
                "actual_productivity_kg_ha": 0,
                "productivity_delta_percent": 0,
                "max_safe_loss_rate_percent": 0,
                "actual_loss_rate_percent": 0,
                "loss_delta_percent": 0,
                "actual_roi_percent": 0,
                "recommendations": ["Belum ada data panen yang tercatat untuk dianalisis."]
            }

        # 1. Kalkulasi Agregat Luas dan Volume Panen
        total_kg = sum(r.harvest_quantity_kg for r in records)
        total_area = sum(r.land_area_ha for r in records)
        total_damaged = sum(r.damaged_quantity_kg for r in records)
        total_rev = sum(r.gross_revenue for r in records)
        total_cost = sum(r.total_production_cost for r in records)
        total_profit = sum(r.net_profit for r in records)

        avg_prod = (total_kg / total_area) if total_area > 0 else 0
        actual_loss_pct = (total_damaged / total_kg * 100) if total_kg > 0 else 0
        avg_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
        rc_ratio = (total_rev / total_cost) if total_cost > 0 else 1.0

        # 2. Perhitungan Standar Benchmark Tertimbang (Weighted Benchmark)
        # Jika filter komoditas spesifik dipilih, gunakan benchmark komoditas tsb.
        # Jika multi-komoditas, hitung rata-rata berbobot luas lahan (weighted average).
        if commodity_filter and commodity_filter in BENCHMARKS:
            target_label = commodity_filter
            std_prod = BENCHMARKS[commodity_filter]["standard_productivity_kg_ha"]
            max_loss = BENCHMARKS[commodity_filter]["max_loss_rate_pct"]
        else:
            target_label = "Agregat Seluruh Komoditas"
            weighted_std_sum = 0.0
            weighted_loss_sum = 0.0
            total_weight = 0.0

            for r in records:
                b = BENCHMARKS.get(r.commodity, DEFAULT_BENCHMARK)
                w = r.land_area_ha if r.land_area_ha > 0 else 0.1
                weighted_std_sum += (b["standard_productivity_kg_ha"] * w)
                weighted_loss_sum += (b["max_loss_rate_pct"] * w)
                total_weight += w

            std_prod = (weighted_std_sum / total_weight) if total_weight > 0 else 5500.0
            max_loss = (weighted_loss_sum / total_weight) if total_weight > 0 else 8.0

        # 3. Deviasi Kinerja Produktivitas & Deviasi Susut
        prod_delta_pct = ((avg_prod - std_prod) / std_prod * 100) if std_prod > 0 else 0
        loss_delta_pct = actual_loss_pct - max_loss

        # 4. Multi-Criteria Scoring Index (Skor 0 - 100)
        prod_score = min(100.0, max(0.0, 50.0 + (prod_delta_pct * 1.5)))
        loss_score = min(100.0, max(0.0, 100.0 - (actual_loss_pct / max_loss * 50.0)))
        roi_score = min(100.0, max(0.0, 50.0 + ((avg_roi - 40.0) * 1.0)))
        composite_score = (prod_score * 0.40) + (loss_score * 0.35) + (roi_score * 0.25)

        # Penentuan Status Grade
        if composite_score >= 82.0 and loss_delta_pct <= 0:
            status_grade = "SUPERIOR"
            status_label = "Sangat Unggul & Efisien"
            badge_color = "#10b981"
            rating_stars = "⭐⭐⭐⭐⭐"
        elif composite_score >= 68.0 and loss_delta_pct <= 3.0:
            status_grade = "OPTIMAL"
            status_label = "Optimal & Sesuai Standar"
            badge_color = "#06b6d4"
            rating_stars = "⭐⭐⭐⭐"
        elif composite_score >= 50.0:
            status_grade = "MODERATE"
            status_label = "Cukup (Perlu Optimasi Minor)"
            badge_color = "#f59e0b"
            rating_stars = "⭐⭐⭐"
        else:
            status_grade = "NEEDS_IMPROVEMENT"
            status_label = "Di Bawah Potensi Maksimal"
            badge_color = "#f43f5e"
            rating_stars = "⭐⭐"

        # 5. Himpun Diagnosa Hama / Kerusakan Lapangan dari Seluruh Record
        pests_detected = {}
        for r in records:
            if hasattr(r, 'pest_disease') and r.pest_disease:
                for p in r.pest_disease:
                    p_name = p.name if hasattr(p, 'name') else p.get('name', '')
                    if p_name:
                        pests_detected[p_name] = pests_detected.get(p_name, 0) + 1

        recommendations = []

        # Rekomendasi Deviasi Kinerja Produktivitas
        if prod_delta_pct >= 15.0:
            recommendations.append(f"🏆 Rata-rata produktivitas lahan istimewa (+{prod_delta_pct:.1f}% di atas standar acuan {std_prod:,.0f} kg/ha). Manajemen agronomi terbukti sangat efektif.")
        elif prod_delta_pct >= 0.0:
            recommendations.append(f"✅ Rata-rata produktivitas lahan stabil dan melampaui standar nasional (+{prod_delta_pct:.1f}% vs {std_prod:,.0f} kg/ha).")
        elif prod_delta_pct >= -15.0:
            recommendations.append(f"⚠️ Rata-rata produktivitas berada {abs(prod_delta_pct):.1f}% di bawah standar acuan ({std_prod:,.0f} kg/ha). Periksa kembali kerapatan bibit dan rotasi tanaman.")
        else:
            recommendations.append(f"🚨 Terjadi penurunan produktivitas signifikan ({abs(prod_delta_pct):.1f}% vs target {std_prod:,.0f} kg/ha). Lakukan pembenahan struktur tanah dan optimasi pupuk dasar NPK/Organik.")

        # Rekomendasi Tingkat Kerusakan
        if loss_delta_pct > 0:
            pest_list_str = f" Teridentifikasi gejala hama dominan: {', '.join(pests_detected.keys())}." if pests_detected else ""
            recommendations.append(
                f"🔍 Tingkat kerusakan susut pasca panen ({actual_loss_pct:.1f}%) melampaui batas toleransi ({max_loss:.1f}%).{pest_list_str} Disarankan peningkatan sanitasi kebun dan penanganan pasca panen yang lebih higienis."
            )
        else:
            recommendations.append(
                f"✨ Mutu panen sangat baik dengan tingkat kerusakan rendah ({actual_loss_pct:.1f}% vs batas toleransi {max_loss:.1f}%)."
            )

        # Rekomendasi Kelayakan Usaha & Finansial
        if rc_ratio >= 1.5:
            recommendations.append(f"💰 Efisiensi ekonomi budidaya sangat tinggi (R/C Ratio {rc_ratio:.2f}, ROI rata-rata {avg_roi:.1f}%). Model pengelolaan kebun ini sangat direkomendasikan untuk diperluas.")
        elif rc_ratio >= 1.15:
            recommendations.append(f"💵 Usaha budidaya menguntungkan dengan ROI rata-rata {avg_roi:.1f}% (R/C Ratio {rc_ratio:.2f}).")
        else:
            recommendations.append(f"💡 Margin profit tipis (ROI rata-rata {avg_roi:.1f}%). Evaluasi biaya input agrokimia/tenaga kerja dan perluas kemitraan serap offtaker.")

        return {
            "target": target_label,
            "status_grade": status_grade,
            "status_label": status_label,
            "badge_color": badge_color,
            "rating_stars": rating_stars,
            "composite_score": round(composite_score, 1),
            "benchmark_productivity_kg_ha": round(std_prod, 1),
            "actual_productivity_kg_ha": round(avg_prod, 1),
            "productivity_delta_percent": round(prod_delta_pct, 1),
            "max_safe_loss_rate_percent": round(max_loss, 1),
            "actual_loss_rate_percent": round(actual_loss_pct, 1),
            "loss_delta_percent": round(loss_delta_pct, 1),
            "rc_ratio": round(rc_ratio, 2),
            "actual_roi_percent": round(avg_roi, 1),
            "recommendations": recommendations,
            "insights": recommendations
        }

    # Backward compatibility alias
    def evaluate_summary_data(self, summary_data: Dict[str, Any], commodity_filter: Optional[str] = None) -> Dict[str, Any]:
        return self.evaluate_records_collection([], commodity_filter)


ai_insight_service = AIInsightService()
