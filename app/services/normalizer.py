from typing import Tuple


class UnitNormalizer:
    """Mengonversi berbagai satuan lokal/internasional ke satuan standar (kg & ha)."""

    AREA_CONVERSIONS = {
        "ha": 1.0,
        "hektare": 1.0,
        "hectare": 1.0,
        "m2": 0.0001,
        "meter_persegi": 0.0001,
        "are": 0.01,
        "bata": 0.0014,     # 1 bata = 14 m² (Jawa Barat/Tengah)
        "ru": 0.0014,       # 1 ru = 14 m² (Jawa Timur)
        "tumbak": 0.0014,   # 1 tumbak = 14 m²
        "ubin": 0.0014      # 1 ubin = 14.06 m² ~ 0.0014 ha
    }

    WEIGHT_CONVERSIONS = {
        "kg": 1.0,
        "kilogram": 1.0,
        "ton": 1000.0,
        "ton_metrik": 1000.0,
        "kuintal": 100.0,
        "kw": 100.0,
        "gram": 0.001,
        "peti": 30.0,       # Estimasi rata-rata 1 peti cabai/tomat = 30 kg
        "karung": 50.0,     # Rata-rata 1 karung padi/jagung = 50 kg
        "ikat": 1.0         # Default perkiraan sayuran daun = 1 kg
    }

    @classmethod
    def normalize_area_to_ha(cls, area: float, unit: str) -> float:
        cleaned_unit = unit.lower().strip()
        factor = cls.AREA_CONVERSIONS.get(cleaned_unit, 1.0)
        return round(area * factor, 4)

    @classmethod
    def normalize_weight_to_kg(cls, weight: float, unit: str) -> float:
        cleaned_unit = unit.lower().strip()
        factor = cls.WEIGHT_CONVERSIONS.get(cleaned_unit, 1.0)
        return round(weight * factor, 3)

    @classmethod
    def normalize_price_per_kg(cls, price_per_unit: float, unit: str) -> float:
        """Menghitung ekuivalen harga per kg jika harga diinput per ton/kuintal/peti."""
        cleaned_unit = unit.lower().strip()
        factor = cls.WEIGHT_CONVERSIONS.get(cleaned_unit, 1.0)
        if factor == 0:
            return price_per_unit
        return round(price_per_unit / factor, 2)
