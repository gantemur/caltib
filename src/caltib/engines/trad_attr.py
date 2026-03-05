"""
caltib.engines.trad_attr
------------------------
Implementation of the Traditional Astrological Attributes Engine.
Outputs flexible dictionaries containing 0-indexed attribute IDs.
"""
from typing import Dict, Any
from caltib.engines.interfaces import AttributeEngineProtocol

class TraditionalAttributeEngine(AttributeEngineProtocol):
    def __init__(self, engine_id: str = "mongol"):
        self.is_phugpa = (engine_id.lower() == "phugpa")

    def get_year_attributes(self, tib_year: int) -> Dict[str, Any]:
        """Calculates Chinese 60-year cycle attributes for a given Tibetan Year."""
        return {
            "animal": (tib_year - 4) % 12,
            "element": ((tib_year - 4) // 2) % 5,
            "gender": (tib_year - 4) % 2,
            "mewa": (1 - tib_year) % 9 + 1  # 1-indexed (1-9)
        }

    def get_month_attributes(self, tib_year: int, month_no: int) -> Dict[str, Any]:
        """Calculates attributes for a lunar month."""
        if self.is_phugpa:
            animal = (month_no + 3) % 12
            if month_no <= 10:
                element = (tib_year // 2 + (month_no + 1) // 2 - 1) % 5
            else:
                element = ((tib_year + 1) // 2 + (month_no - 11) // 2 - 1) % 5
        else:
            animal = (month_no + 1) % 12
            element = (tib_year - 3 + (month_no - 1) // 2) % 5
            
        return {
            "animal": animal,
            "element": element,
            "gender": 1 - (month_no % 2),
            "mewa": (2 - 12 * tib_year - month_no) % 9 + 1
        }

    def get_lunar_day_attributes(self, tib_year: int, month_no: int, tithi: int) -> Dict[str, Any]:
        """Calculates attributes for a tithi, cascading from the month's base attributes."""
        m_attr = self.get_month_attributes(tib_year, month_no)
        m_animal = m_attr["animal"]
        
        return {
            "animal": (tithi + 6 * m_animal + 1) % 12,
            "element": (m_attr["element"] + tithi) % 5,
            "mewa": (tithi + 3 * m_animal + 2) % 9 + 1,
            "trigram": (tithi + 6 * m_animal + 3) % 8
        }

    def get_civil_day_attributes(self, jdn: int) -> Dict[str, Any]:
        """Calculates absolute attributes based strictly on the Julian Day Number."""
        return {
            "animal": (jdn + 1) % 12,
            "element": ((jdn - 1) // 2) % 5,
            "gender": (jdn + 1) % 2,
            "mewa": (-jdn - 1) % 9 + 1,
            "trigram": (jdn + 1) % 8,
            "day_of_week": (jdn + 1) % 7
        }