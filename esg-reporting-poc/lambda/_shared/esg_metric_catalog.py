"""What the group is expected to report, per metric: the Data Hub compares this with the data and raises an alert for
every metric that is missing, so a gap is shown as a gap and never as zero.

Environmental metrics are derived from the activity ledger (esg_raw.activity_data); social, governance and finance
metrics come from esg_raw.esg_metric. ``applies`` lists entity types, or "all".
"""

from __future__ import annotations

LENDING = ["bank", "sharia_bank", "multifinance"]

# conversion of activity quantities to energy, GJ per unit (GRI 302-1)
ENERGY_GJ = {"electricity_grid": 0.0036, "solar_pv": 0.0036, "natural_gas": 1.0, "diesel_stationary": 0.0361, "diesel_fleet": 0.0361,
             "gasoline_fleet": 0.0330}

ENTITY_TYPES = {"bank": "Bank", "sharia_bank": "Sharia bank", "multifinance": "Multifinance", "securities": "Securities", "insurance": "Insurance"}

METRICS: list[dict] = [
    # environment (derived from activity data)
    {"id": "energy_total_gj", "pillar": "environment", "topic": "energy", "label": "Energy consumption", "unit": "GJ", "ref": "GRI 302-1", "applies": "all", "required": True},
    {"id": "electricity_mwh", "pillar": "environment", "topic": "energy", "label": "Electricity consumption", "unit": "MWh", "ref": "GRI 302-1", "applies": "all", "required": True},
    {"id": "renewable_share_pct", "pillar": "environment", "topic": "energy", "label": "Renewable electricity (on-site + certificates)", "unit": "%", "ref": "GRI 302-1 / IFRS S2", "applies": "all", "required": False},
    {"id": "energy_intensity_gj_per_fte", "pillar": "environment", "topic": "energy", "label": "Energy intensity", "unit": "GJ/FTE", "ref": "GRI 302-3", "applies": "all", "required": False},
    {"id": "water_withdrawal_m3", "pillar": "environment", "topic": "water", "label": "Water withdrawal", "unit": "m3", "ref": "GRI 303-3", "applies": "all", "required": True},
    {"id": "water_discharge_m3", "pillar": "environment", "topic": "water", "label": "Water discharge", "unit": "m3", "ref": "GRI 303-4", "applies": "all", "required": False},
    {"id": "waste_total_t", "pillar": "environment", "topic": "waste", "label": "Waste generated", "unit": "t", "ref": "GRI 306-3", "applies": "all", "required": True},
    {"id": "waste_diverted_pct", "pillar": "environment", "topic": "waste", "label": "Waste diverted from disposal (recycled)", "unit": "%", "ref": "GRI 306-4", "applies": "all", "required": False},
    {"id": "paper_reams", "pillar": "environment", "topic": "materials", "label": "Paper use", "unit": "reams", "ref": "GRI 301-1 / POJK 51", "applies": "all", "required": True},
    # social
    {"id": "headcount", "pillar": "social", "topic": "workforce", "label": "Employees", "unit": "people", "ref": "GRI 2-7", "applies": "all", "required": True},
    {"id": "female_pct", "pillar": "social", "topic": "diversity", "label": "Women in the workforce", "unit": "%", "ref": "GRI 405-1", "applies": "all", "required": True},
    {"id": "female_management_pct", "pillar": "social", "topic": "diversity", "label": "Women in management", "unit": "%", "ref": "GRI 405-1", "applies": "all", "required": True},
    {"id": "employees_with_disability", "pillar": "social", "topic": "diversity", "label": "Employees with disabilities", "unit": "people", "ref": "POJK 51/2017 social", "applies": "all", "required": True},
    {"id": "remuneration_ratio_female_male", "pillar": "social", "topic": "diversity", "label": "Remuneration ratio women to men", "unit": "ratio", "ref": "GRI 405-2", "applies": "all", "required": False},
    {"id": "new_hires", "pillar": "social", "topic": "workforce", "label": "New hires", "unit": "people", "ref": "GRI 401-1", "applies": "all", "required": True},
    {"id": "turnover_voluntary_pct", "pillar": "social", "topic": "workforce", "label": "Voluntary turnover", "unit": "%", "ref": "GRI 401-1", "applies": "all", "required": True},
    {"id": "training_hours_per_fte", "pillar": "social", "topic": "training", "label": "Training hours per employee", "unit": "hours", "ref": "GRI 404-1", "applies": "all", "required": True},
    {"id": "lost_time_injuries", "pillar": "social", "topic": "health_safety", "label": "Lost-time injuries", "unit": "cases", "ref": "GRI 403-9", "applies": "all", "required": True},
    {"id": "fatalities", "pillar": "social", "topic": "health_safety", "label": "Work-related fatalities", "unit": "cases", "ref": "GRI 403-9", "applies": "all", "required": True},
    {"id": "community_investment_idr", "pillar": "social", "topic": "community", "label": "Community investment", "unit": "IDR", "ref": "GRI 203-1 / POJK 51", "applies": "all", "required": True},
    {"id": "financial_literacy_participants", "pillar": "social", "topic": "community", "label": "Financial literacy participants", "unit": "people", "ref": "POJK 51/2017 social", "applies": "all", "required": False},
    {"id": "customer_complaints", "pillar": "social", "topic": "customers", "label": "Customer complaints", "unit": "cases", "ref": "POJK 51/2017 social", "applies": "all", "required": True},
    {"id": "complaints_resolved_pct", "pillar": "social", "topic": "customers", "label": "Complaints resolved", "unit": "%", "ref": "POJK 51/2017 social", "applies": "all", "required": False},
    # governance
    {"id": "board_members", "pillar": "governance", "topic": "board", "label": "Board members", "unit": "people", "ref": "GRI 2-9", "applies": "all", "required": True},
    {"id": "independent_commissioner_pct", "pillar": "governance", "topic": "board", "label": "Independent commissioners", "unit": "%", "ref": "GRI 2-9 / POJK 55/2016", "applies": "all", "required": True},
    {"id": "female_board_pct", "pillar": "governance", "topic": "board", "label": "Women on the board", "unit": "%", "ref": "GRI 405-1", "applies": "all", "required": False},
    {"id": "anti_corruption_training_pct", "pillar": "governance", "topic": "ethics", "label": "Anti-corruption training coverage", "unit": "%", "ref": "GRI 205-2", "applies": "all", "required": True},
    {"id": "confirmed_corruption_cases", "pillar": "governance", "topic": "ethics", "label": "Confirmed corruption cases", "unit": "cases", "ref": "GRI 205-3", "applies": "all", "required": True},
    {"id": "whistleblowing_reports", "pillar": "governance", "topic": "ethics", "label": "Whistleblowing reports", "unit": "reports", "ref": "POJK 51/2017 governance", "applies": "all", "required": False},
    {"id": "regulatory_fines_idr", "pillar": "governance", "topic": "compliance", "label": "Regulatory fines", "unit": "IDR", "ref": "GRI 2-27", "applies": "all", "required": True},
    {"id": "data_breaches", "pillar": "governance", "topic": "privacy", "label": "Customer data breaches", "unit": "incidents", "ref": "GRI 418-1", "applies": "all", "required": True},
    {"id": "esg_committee", "pillar": "governance", "topic": "oversight", "label": "Board-level ESG committee", "unit": "yes/no", "ref": "IFRS S2 para 6", "applies": "all", "required": False},
    # finance
    {"id": "loan_book_idr", "pillar": "finance", "topic": "loan_book", "label": "Loan / financing book", "unit": "IDR", "ref": "POJK 51/2017", "applies": LENDING, "required": True},
    {"id": "sustainable_finance_idr", "pillar": "finance", "topic": "sustainable_finance", "label": "Sustainable finance (KUBL)", "unit": "IDR", "ref": "POJK 51/2017 KUBL / TKBI", "applies": LENDING, "required": True},
    {"id": "financed_tco2e", "pillar": "finance", "topic": "financed_emissions", "label": "Financed emissions (Scope 3 cat. 15)", "unit": "tCO2e", "ref": "PCAF Part A", "applies": LENDING, "required": True},
]
BY_ID = {m["id"]: m for m in METRICS}

KUBL_LABELS = {"renewable_energy": "Renewable energy", "energy_efficiency": "Energy efficiency", "green_building": "Green buildings",
               "clean_transportation": "Clean transportation", "sustainable_agriculture": "Sustainable agriculture and natural resources",
               "pollution_prevention": "Pollution prevention", "water_waste_management": "Water and waste management", "msme": "MSME (UMKM)"}

# activity types every facility must report each month; annual items once a year
MONTHLY_REQUIRED = ["electricity_grid", "water_supply", "waste_landfill", "paper_a4"]
ANNUAL_REQUIRED = ["refrigerant_r410a"]

ACTIVITY_LABELS = {
    "electricity_grid": "Grid electricity", "solar_pv": "On-site solar", "natural_gas": "Natural gas", "diesel_stationary": "Diesel (gensets)",
    "gasoline_fleet": "Fleet gasoline", "diesel_fleet": "Fleet diesel", "refrigerant_r410a": "Refrigerant R-410A", "refrigerant_r32": "Refrigerant R-32",
    "paper_a4": "Paper", "water_supply": "Water supply", "waste_landfill": "Waste to landfill", "waste_recycled": "Waste recycled",
    "air_travel_domestic": "Air travel, domestic", "air_travel_international": "Air travel, international", "hotel_night": "Hotel nights",
    "commute_car": "Commuting by car", "commute_motorcycle": "Commuting by motorcycle", "commute_public": "Commuting by public transport",
}
CATEGORY_LABELS = {
    "s1_stationary": "Scope 1 · stationary combustion", "s1_mobile": "Scope 1 · mobile combustion", "s1_fugitive": "Scope 1 · fugitive (refrigerants)",
    "s2_electricity": "Scope 2 · purchased electricity", "s2_renewable": "Scope 2 · on-site renewable", "c1_purchased_goods": "Scope 3 · cat. 1 purchased goods",
    "c5_waste": "Scope 3 · cat. 5 waste", "c6_business_travel": "Scope 3 · cat. 6 business travel", "c7_commuting": "Scope 3 · cat. 7 commuting",
}
EF_SETS = {"ID_NATIONAL": "National grid average (reported basis)", "ID_REGIONAL": "Regional grid factors by electricity system"}
APPROACHES = {"control": "Operational control", "equity": "Equity share"}

# group target (synthetic): Scope 1 + 2 market-based -30 % by 2030 against the 2023 base year, linear path
TARGET = {"label": "Scope 1 + 2 (market-based) -30 % by 2030 vs 2023", "base_year": 2023, "target_year": 2030, "reduction_pct": 30.0}
