"""Domain configuration shared by the scenario engine, portfolio analytics and GHG inventory.

All sector parameters are explicit ASSUMPTIONS for demonstration. They are meant to be replaced by the
bank's own models and by the official TKBI taxonomy mapping before any external disclosure.
"""

from __future__ import annotations

import re
from typing import Any

# ── Sector profiles (keys are the NACE-style codes used in the synthetic loan book) ─────────────
# sens   : share of EBITDA lost per USD 100/tCO2e carbon price (transition sensitivity)
# split  : assumed TKBI-style classification of the sector's lending (green / transition / brown)
SECTOR_PROFILES: dict[str, dict[str, Any]] = {
    "energy_oil_gas": {"name": "Energy: oil & gas", "sens": 0.38, "high_emission": True, "split": (0.04, 0.26, 0.70), "keywords": ("oil", "gas")},
    "manufacturing_cement": {"name": "Manufacturing: cement", "sens": 0.30, "high_emission": True, "split": (0.05, 0.45, 0.50), "keywords": ("cement",)},
    "manufacturing_steel": {"name": "Manufacturing: steel", "sens": 0.30, "high_emission": True, "split": (0.05, 0.50, 0.45), "keywords": ("steel",)},
    "transportation_road": {"name": "Transportation: road", "sens": 0.15, "high_emission": False, "split": (0.12, 0.58, 0.30), "keywords": ("transport",)},
    "agriculture": {"name": "Agriculture", "sens": 0.12, "high_emission": False, "split": (0.20, 0.55, 0.25), "keywords": ("agri",)},
    "manufacturing_food": {"name": "Manufacturing: food", "sens": 0.05, "high_emission": False, "split": (0.18, 0.62, 0.20), "keywords": ("food",)},
    "real_estate_commercial": {"name": "Real estate: commercial", "sens": 0.06, "high_emission": False, "split": (0.22, 0.58, 0.20), "keywords": ("commercial",)},
    "real_estate_residential": {"name": "Real estate: residential", "sens": 0.03, "high_emission": False, "split": (0.25, 0.60, 0.15), "keywords": ("residential",)},
    "retail_trade": {"name": "Retail trade", "sens": 0.03, "high_emission": False, "split": (0.15, 0.70, 0.15), "keywords": ("retail",)},
    "financial_services": {"name": "Financial services", "sens": 0.02, "high_emission": False, "split": (0.30, 0.60, 0.10), "keywords": ("financial",)},
}
DEFAULT_PROFILE = {"name": "Other", "sens": 0.05, "high_emission": False, "split": (0.15, 0.60, 0.25), "keywords": ()}


def sector_profile(code_or_name: str) -> tuple[str, dict[str, Any]]:
    """Resolve a NACE-style code OR a display name to (code, profile). Falls back to DEFAULT_PROFILE."""
    s = (code_or_name or "").strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if key in SECTOR_PROFILES:
        return key, SECTOR_PROFILES[key]
    for code, prof in SECTOR_PROFILES.items():
        if all(kw in s for kw in prof["keywords"]) and prof["keywords"]:
            # real estate needs both word groups to disambiguate commercial / residential
            if code.startswith("real_estate") and "real" not in s and "estate" not in s and "property" not in s:
                continue
            return code, prof
    return key or "other", DEFAULT_PROFILE


# ── Loan-type → PCAF asset class ───────────────────────────────────────────────────────────────
PCAF_ASSET_CLASSES = {
    "corp": "Business loans & unlisted equity",
    "listed": "Listed equity & corporate bonds",
    "pf": "Project finance",
    "cre": "Commercial real estate",
    "mort": "Mortgages",
    "mv": "Motor vehicle loans",
}


def asset_class_for(loan_type: str, sector: str) -> str:
    lt = (loan_type or "").lower()
    if lt == "project_finance":
        return "pf"
    if lt == "mortgage":
        return "mort"
    if lt == "leasing":
        return "mv"
    if "real_estate_commercial" in (sector or "").lower():
        return "cre"
    return "corp"


# ── Emission factors used to split Scope 1 by gas (IPCC 2006 stationary combustion defaults) ──────
# kg per GJ (natural gas) / kg per litre (diesel). CO2e conversion uses AR6 GWP100 (fossil CH4, N2O).
GWP = {"CH4": 29.8, "N2O": 273.0}
SCOPE1_GAS_FACTORS = {
    "natural_gas_per_gj": {"CO2": 56.10, "CH4": 0.0010, "N2O": 0.0001},
    "diesel_per_litre": {"CO2": 2.6710, "CH4": 0.00029, "N2O": 0.00003308},
}

# ── Operational Scope 3 (categories 1-7) default spend/activity-based factors ──────────────────────
SCOPE3_OPERATIONAL_CATEGORIES = {
    "c1": "Cat 1 · Purchased goods and services",
    "c2": "Cat 2 · Capital goods",
    "c3": "Cat 3 · Fuel- and energy-related activities",
    "c4": "Cat 4 · Upstream transportation and distribution",
    "c5": "Cat 5 · Waste generated in operations",
    "c6": "Cat 6 · Business travel",
    "c7": "Cat 7 · Employee commuting",
}
