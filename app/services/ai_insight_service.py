from typing import Dict, Any, Optional
from datetime import datetime

# Standar Benchmark Komoditas Pertanian Nasional (BPS & Kementan RI)
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
        "optimal_price_idr_kg": 6000.0,
        "category": "Pangan"
    },
    "Jagung Pipil": {
        "standard_productivity_kg_ha": 6500.0,
        "max_loss_rate_pct": 6.0,
        "standard_roi_pct": 45.0,
        "optimal_price_idr_kg": 4800.0,
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
    "standard_productivity_kg_ha": 5000.0,
    "max_loss_rate_pct": 10.0,
    "standard_roi_pct": 40.0,
    "optimal_price_idr_kg": 15000.0,
    "category": "Umum"
}


class AIInsightService:
    """Service untuk komparasi benchmark produktivitas dan rekomendasi cerdas agronomi."""

    def evaluate_harvest_record(self, record: Any) -> Dict[str, Any]:
        commodity = record.commodity
        benchmark = BENCHMARKS.get(commodity, DEFAULT_BENCHMARK)
        std_prod = benchmark["standard_productivity_kg_ha"]
        max_loss = benchmark["max_loss_rate_pct"]

        kpi = record.kpi_summary
        prod_kpi = kpi.production_kpis if kpi else None
        econ_kpi = kpi.economic_kpis if kpi else None

        actual_prod = prod_kpi.productivity_kg_per_ha if prod_kpi else ((record.harvest_quantity_kg / record.land_area_ha) if record.land_area_ha > 0 else 0)
        actual_loss = prod_kpi.loss_rate_percent if prod_kpi else ((record.damaged_quantity_kg / record.harvest_quantity_kg * 100) if record.harvest_quantity_kg > 0 else 0)
        actual_roi = econ_kpi.roi_percent if econ_kpi else (((record.net_profit / record.total_production_cost) * 100) if record.total_production_cost > 0 else 0)

        prod_delta_pct = ((actual_prod - std_prod) / std_prod * 100) if std_prod > 0 else 0

        # Status Grade
        if prod_delta_pct >= 10.0 and actual_loss <= max_loss:
            status_grade = "SUPERIOR"
            status_label = "Sangat Unggul & Efisien"
            badge_color = "#10b981" # emerald
            rating_stars = "⭐⭐⭐⭐⭐"
        elif prod_delta_pct >= -5.0 and actual_loss <= max_loss * 1.3:
            status_grade = "OPTIMAL"
            status_label = "Optimal & Sesuai Standar"
            badge_color = "#06b6d4" # cyan
            rating_stars = "⭐⭐⭐⭐"
        elif prod_delta_pct >= -20.0:
            status_grade = "MODERATE"
            status_label = "Cukup (Perlu Optimasi Minor)"
            badge_color = "#f59e0b" # amber
            rating_stars = "⭐⭐⭐"
        else:
            status_grade = "NEEDS_IMPROVEMENT"
            status_label = "Di Bawah Potensi Maksimal"
            badge_color = "#f43f5e" # rose
            rating_stars = "⭐⭐"

        # Rekomendasi agronomi terarah
        recommendations = []

        if prod_delta_pct > 15:
            recommendations.append(f"🏆 Produktivitas istimewa (+{prod_delta_pct:.1f}% di atas standar {std_prod:,.0f} kg/ha). Pertahankan protokol pemupukan dan irigasi.")
        elif prod_delta_pct < -10:
            recommendations.append(f"⚠️ Produktivitas berada {abs(prod_delta_pct):.1f}% di bawah potensi standar ({std_prod:,.0f} kg/ha). Evaluasi kepadatan populasi tanam (jarak tanam) dan uji kesuburan tanah (pH/NPK).")
        else:
            recommendations.append(f"✅ Produktivitas stabil memenuhi standar komoditas {commodity}.")

        if actual_loss > max_loss:
            recommendations.append(f"🔍 Tingkat kerusakan {actual_loss:.1f}% melampaui batas aman ({max_loss:.1f}%). Tingkatkan pencegahan hama terpadu (PHT) dan kecepatan pengangkutan pasca panen.")
        else:
            recommendations.append(f"✨ Kualitas panen terjaga prima dengan tingkat kerusakan rendah ({actual_loss:.1f}%).")

        if actual_roi > 70:
            recommendations.append(f"💰 Efisiensi biaya luar biasa dengan ROI {actual_roi:.1f}%. Model budidaya ini sangat layak direplikasi.")
        elif actual_roi < 25:
            recommendations.append(f"💡 Margin profit tipis (ROI {actual_roi:.1f}%). Evaluasi biaya input agrokimia/tenaga kerja dan perluas kemitraan serap langsung (offtaker).")

        return {
            "commodity": commodity,
            "status_grade": status_grade,
            "status_label": status_label,
            "badge_color": badge_color,
            "rating_stars": rating_stars,
            "benchmark_productivity_kg_ha": std_prod,
            "actual_productivity_kg_ha": round(actual_prod, 1),
            "productivity_delta_percent": round(prod_delta_pct, 1),
            "max_safe_loss_rate_percent": max_loss,
            "actual_loss_rate_percent": round(actual_loss, 1),
            "actual_roi_percent": round(actual_roi, 1),
            "recommendations": recommendations,
        }

    def evaluate_summary_data(self, summary_data: Dict[str, Any], commodity_filter: Optional[str] = None) -> Dict[str, Any]:
        comm = commodity_filter if commodity_filter else "Agregat Seluruh Komoditas"
        benchmark = BENCHMARKS.get(commodity_filter, DEFAULT_BENCHMARK) if commodity_filter else DEFAULT_BENCHMARK

        avg_prod = summary_data.get("avg_productivity_kg_per_ha", 0)
        avg_marketable = summary_data.get("avg_marketable_yield_percent", 0)
        avg_loss = 100.0 - avg_marketable if avg_marketable > 0 else 0
        avg_roi = summary_data.get("avg_roi_percent", 0)
        std_prod = benchmark["standard_productivity_kg_ha"]
        max_loss = benchmark["max_loss_rate_pct"]

        prod_delta = ((avg_prod - std_prod) / std_prod * 100) if std_prod > 0 else 0

        # Status Grade
        if prod_delta >= 10.0 and avg_loss <= max_loss:
            status_grade = "SUPERIOR"
            status_label = "Sangat Unggul & Efisien"
            badge_color = "#10b981" # emerald
            rating_stars = "⭐⭐⭐⭐⭐"
        elif prod_delta >= -5.0 and avg_loss <= max_loss * 1.3:
            status_grade = "OPTIMAL"
            status_label = "Optimal & Sesuai Standar"
            badge_color = "#06b6d4" # cyan
            rating_stars = "⭐⭐⭐⭐"
        elif prod_delta >= -20.0:
            status_grade = "MODERATE"
            status_label = "Cukup (Perlu Optimasi Minor)"
            badge_color = "#f59e0b" # amber
            rating_stars = "⭐⭐⭐"
        else:
            status_grade = "NEEDS_IMPROVEMENT"
            status_label = "Di Bawah Potensi Maksimal"
            badge_color = "#f43f5e" # rose
            rating_stars = "⭐⭐"

        recommendations = []
        if prod_delta > 15:
            recommendations.append(f"🏆 Produktivitas rata-rata lahan sangat istimewa (+{prod_delta:.1f}% vs standar nasional {std_prod:,.0f} kg/ha). Pertahankan nutrisi berimbang & SOP budidaya.")
        elif prod_delta < -10:
            recommendations.append(f"⚠️ Rata-rata produktivitas berada {abs(prod_delta):.1f}% di bawah target standar ({std_prod:,.0f} kg/ha). Periksa kembali kerapatan bibit dan rotasi tanaman.")
        else:
            recommendations.append(f"✅ Produktivitas berjalan stabil dan selaras dengan standar acuan ({std_prod:,.0f} kg/ha).")

        if avg_loss <= max_loss:
            recommendations.append(f"✨ Kualitas mutu tinggi dengan tingkat kehilangan/rusak rendah ({avg_loss:.1f}% vs ambang batas {max_loss:.1f}%).")
        else:
            recommendations.append(f"🔍 Tingkat kerusakan ({avg_loss:.1f}%) melebihi toleransi ({max_loss:.1f}%). Tingkatkan pencegahan hama terpadu (PHT) dan percepat distribusi pasca panen.")

        if avg_roi > 50:
            recommendations.append(f"💰 Efisiensi ekonomi budidaya sangat sehat dengan ROI rata-rata {avg_roi:.1f}%.")
        elif avg_roi < 25:
            recommendations.append(f"💡 Margin tipis (ROI rata-rata {avg_roi:.1f}%). Evaluasi biaya input agrokimia/tenaga kerja dan perluas kemitraan serap offtaker.")

        return {
            "target": comm,
            "status_grade": status_grade,
            "status_label": status_label,
            "badge_color": badge_color,
            "rating_stars": rating_stars,
            "benchmark_productivity_kg_ha": std_prod,
            "actual_productivity_kg_ha": round(avg_prod, 1),
            "productivity_delta_percent": round(prod_delta, 1),
            "max_safe_loss_rate_percent": max_loss,
            "actual_loss_rate_percent": round(avg_loss, 1),
            "actual_roi_percent": round(avg_roi, 1),
            "recommendations": recommendations,
            "insights": recommendations
        }


ai_insight_service = AIInsightService()
