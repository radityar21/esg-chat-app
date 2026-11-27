"""Data contracts for the tables extracted from the source database, and the pure-Python checker.

The Glue job (esg_extract_rds.py) gathers cheap statistics with Spark and calls ``evaluate``; the checker has no
dependencies so it is unit-tested (tests/test_contracts.py) and the same rules explain failures to the user.

Levels:
  blocking  the data cannot be used (missing column, wrong type, no rows, duplicate keys, null keys). The job fails
            BEFORE writing to the raw zone so a broken load never overwrites good data.
  warning   the data is usable but suspicious (values outside the documented range, unexpected category, many nulls).
            The load goes ahead and the warning travels with the report.
"""

from __future__ import annotations

from typing import Any

NUMERIC = {"double", "float", "int", "bigint", "smallint", "decimal", "long", "integer"}
INTEGRAL = {"int", "bigint", "smallint", "long", "integer"}

CONTRACTS: dict[str, dict[str, Any]] = {
    "energy_consumption": {
        "partitions": ["reporting_month"], "min_rows": 1, "unique": ["facility_id", "reporting_month"],
        "columns": {
            "facility_id": {"type": "string", "nullable": False},
            "electricity_kwh": {"type": "double", "min": 0, "max": 85000 * 4},
            "natural_gas_gj": {"type": "double", "null_ok": True, "min": 0, "max": 120 * 4},
            "diesel_liters": {"type": "double", "null_ok": True, "min": 0, "max": 3500 * 4},
            "srec_mwh_claimed": {"type": "double", "min": 0},
            "grid_ef_kgco2_kwh": {"type": "double", "min": 0.0001, "max": 2},
            "ef_source": {"type": "string"},
            "meter_reading_kwh": {"type": "double", "null_ok": True, "min": 0},
            "data_source": {"type": "string", "enum": ["smart_meter_api", "manual_entry", "estimate"]},
            "record_status": {"type": "string", "nullable": False, "enum": ["complete", "missing_primary", "excluded"]},
            "reporting_month": {"type": "int", "nullable": False, "min": 1, "max": 12},
        },
    },
    "loan_portfolio": {
        "partitions": [], "min_rows": 1, "unique": ["loan_id"],
        "columns": {
            "loan_id": {"type": "string", "nullable": False}, "borrower_id": {"type": "string", "nullable": False},
            "sector_nace": {"type": "string", "nullable": False, "enum": [
                "manufacturing_cement", "manufacturing_steel", "manufacturing_food", "real_estate_commercial", "real_estate_residential",
                "transportation_road", "agriculture", "energy_oil_gas", "financial_services", "retail_trade"]},
            "loan_type": {"type": "string", "enum": ["term_loan", "revolving_credit", "mortgage", "project_finance", "syndicated_loan", "leasing"]},
            "currency": {"type": "string", "enum": ["IDR", "USD"]},
            "outstanding_idr": {"type": "bigint", "nullable": False, "min": 1},
            "total_equity_idr": {"type": "bigint", "min": 1}, "total_debt_idr": {"type": "bigint", "min": 0},
            "pcaf_attribution_factor": {"type": "double", "min": 0, "max": 1},
            "borrower_emissions_tco2e": {"type": "double", "min": 0, "max": 5_000_000},
            "pcaf_data_quality_score": {"type": "double", "min": 1, "max": 5},
            "record_status": {"type": "string", "nullable": False, "enum": ["validated", "pending", "rejected"]},
        },
    },
    "hr_metrics": {
        "partitions": [], "min_rows": 1, "unique": [],
        "columns": {
            "period_date": {"type": "date", "nullable": False}, "fte_total": {"type": "int", "nullable": False, "min": 1, "max": 50000},
            "fte_female_pct": {"type": "double", "min": 0, "max": 100}, "fte_management_female_pct": {"type": "double", "min": 0, "max": 100},
            "new_hire_count": {"type": "int", "min": 0}, "voluntary_turnover_pct": {"type": "double", "min": 0, "max": 100},
            "training_hours_per_fte": {"type": "double", "min": 0, "max": 400}, "discrimination_cases": {"type": "int", "min": 0},
        },
    },
    "scope3_operational_activity": {
        "partitions": [], "min_rows": 1, "unique": ["category", "activity"],
        "columns": {
            "category": {"type": "string", "nullable": False, "enum": ["c1", "c2", "c3", "c4", "c5", "c6", "c7"]},
            "activity": {"type": "string", "nullable": False}, "unit": {"type": "string"},
            "quantity": {"type": "double", "min": 0}, "ef_kgco2e_per_unit": {"type": "double", "min": 0},
            "emissions_tco2e": {"type": "double", "min": 0}, "method": {"type": "string"}, "ef_source": {"type": "string"},
            "data_quality_score": {"type": "int", "min": 1, "max": 5},
        },
    },
    # ── group data (scripts/generate_group_data.py) ──
    "entity": {
        "partitions": [], "min_rows": 1, "unique": ["entity_id"],
        "columns": {
            "entity_id": {"type": "string", "nullable": False}, "entity_name": {"type": "string", "nullable": False},
            "entity_type": {"type": "string", "nullable": False, "enum": ["bank", "sharia_bank", "multifinance", "securities", "insurance"]},
            "parent_entity_id": {"type": "string", "null_ok": True},
            "ownership_pct": {"type": "double", "nullable": False, "min": 0, "max": 100},
            "operational_control": {"type": "boolean", "nullable": False}, "country": {"type": "string"}, "consolidation_note": {"type": "string"},
        },
    },
    "facility": {
        "partitions": [], "min_rows": 1, "unique": ["facility_id"],
        "columns": {
            "facility_id": {"type": "string", "nullable": False}, "entity_id": {"type": "string", "nullable": False},
            "facility_name": {"type": "string"},
            "facility_type": {"type": "string", "nullable": False, "enum": ["headquarters", "regional_office", "data_centre", "branch", "warehouse"]},
            "grid_region": {"type": "string", "nullable": False, "enum": ["java_bali", "sumatra", "kalimantan", "sulawesi", "nusa_tenggara", "papua_maluku"]},
            "province": {"type": "string"}, "city": {"type": "string"},
            "floor_area_m2": {"type": "double", "min": 1, "max": 100000}, "headcount": {"type": "int", "min": 0, "max": 10000},
            "ownership_type": {"type": "string", "enum": ["owned", "leased"]}, "opened_year": {"type": "int", "min": 1900, "max": 2100},
            "status": {"type": "string", "enum": ["active", "opened", "closed"]},
        },
    },
    "emission_factor": {
        "partitions": [], "min_rows": 1, "unique": ["ef_set", "activity_type", "region"],
        "columns": {
            "ef_set": {"type": "string", "nullable": False}, "activity_type": {"type": "string", "nullable": False},
            "region": {"type": "string", "nullable": False}, "unit": {"type": "string", "nullable": False},
            "scope": {"type": "int", "nullable": False, "min": 1, "max": 3}, "category": {"type": "string", "nullable": False},
            "co2_kg": {"type": "double", "nullable": False, "min": 0}, "ch4_kg": {"type": "double", "nullable": False, "min": 0},
            "n2o_kg": {"type": "double", "nullable": False, "min": 0}, "co2e_kg": {"type": "double", "nullable": False, "min": 0, "max": 30000},
            "gwp_ch4": {"type": "double", "nullable": False, "min": 1, "max": 100}, "gwp_n2o": {"type": "double", "nullable": False, "min": 100, "max": 400},
            "gwp_basis": {"type": "string"}, "source": {"type": "string"}, "notes": {"type": "string"},
        },
    },
    "activity_data": {
        "partitions": [], "min_rows": 1, "unique": ["activity_id"],
        "columns": {
            "activity_id": {"type": "string", "nullable": False}, "facility_id": {"type": "string", "nullable": False},
            "entity_id": {"type": "string", "nullable": False}, "activity_type": {"type": "string", "nullable": False},
            "quantity": {"type": "double", "nullable": False, "min": 0, "max": 500_000_000}, "unit": {"type": "string", "nullable": False},
            "instrument_qty": {"type": "double", "null_ok": True, "min": 0}, "data_source": {"type": "string"},
            "is_estimated": {"type": "boolean", "nullable": False}, "evidence_ref": {"type": "string", "null_ok": True},
            "reporting_month": {"type": "int", "nullable": False, "min": 1, "max": 12},
        },
    },
    "esg_metric": {
        "partitions": [], "min_rows": 1, "unique": ["entity_id", "metric", "dimension"],
        "columns": {
            "entity_id": {"type": "string", "nullable": False}, "pillar": {"type": "string", "nullable": False, "enum": ["social", "governance", "finance"]},
            "topic": {"type": "string", "nullable": False}, "metric": {"type": "string", "nullable": False},
            "dimension": {"type": "string", "nullable": False}, "value": {"type": "double", "nullable": False},
            "unit": {"type": "string"}, "data_source": {"type": "string"}, "standard_ref": {"type": "string"},
        },
    },
}


def _type_ok(expected: str, actual: str) -> bool:
    actual = actual.lower().split("(")[0]
    if expected == actual:
        return True
    if expected in NUMERIC and actual in NUMERIC:
        # an integer column may widen to a larger integer or a double; a double must not arrive as an integer
        return expected not in INTEGRAL or actual in INTEGRAL or actual == "decimal"
    return False


def evaluate(table: str, stats: dict[str, Any], null_warn_fraction: float = 0.2) -> list[dict[str, Any]]:
    """stats = {"row_count": int, "columns": {name: {"type", "nulls", "min", "max", "distinct": [..]|None}}, "duplicate_keys": int}"""
    spec = CONTRACTS[table]
    out: list[dict[str, Any]] = []

    def add(level: str, rule: str, column: str | None, detail: str) -> None:
        out.append({"level": level, "rule": rule, "column": column, "detail": detail})

    rows = int(stats.get("row_count", 0))
    if rows < spec["min_rows"]:
        add("blocking", "ROWS", None, f"{rows} rows found; at least {spec['min_rows']} expected for this year.")
    cols = stats.get("columns", {})
    for name, rule in spec["columns"].items():
        c = cols.get(name)
        if c is None:
            add("blocking", "MISSING_COLUMN", name, f"Column '{name}' is not present in the source table.")
            continue
        if not _type_ok(rule["type"], str(c.get("type", ""))):
            add("blocking", "TYPE", name, f"Column '{name}' has type {c.get('type')}; expected {rule['type']}.")
            continue
        nulls = int(c.get("nulls", 0))
        if nulls and rule.get("nullable") is False:
            add("blocking", "NULL_KEY", name, f"{nulls} row(s) have no value in required column '{name}'.")
        elif rows and nulls / rows > null_warn_fraction and not rule.get("null_ok"):
            add("warning", "NULLS", name, f"{round(nulls / rows * 100)}% of '{name}' is empty.")
        lo, hi = rule.get("min"), rule.get("max")
        if c.get("min") is not None and lo is not None and c["min"] < lo:
            add("warning", "RANGE", name, f"Minimum of '{name}' is {c['min']}, below the documented minimum {lo}.")
        if c.get("max") is not None and hi is not None and c["max"] > hi:
            add("warning", "RANGE", name, f"Maximum of '{name}' is {c['max']}, above the documented maximum {hi}.")
        allowed = rule.get("enum")
        if allowed and c.get("distinct") is not None:
            unexpected = sorted(set(map(str, c["distinct"])) - set(allowed))
            if unexpected:
                add("warning", "ENUM", name, f"Unexpected value(s) in '{name}': {', '.join(unexpected[:5])}.")
    for extra in sorted(set(cols) - set(spec["columns"])):
        add("warning", "EXTRA_COLUMN", extra, f"Column '{extra}' is not part of the contract and will be ignored by downstream jobs.")
    dup = int(stats.get("duplicate_keys", 0))
    if dup:
        add("blocking", "DUPLICATE_KEYS", ",".join(spec["unique"]), f"{dup} duplicated key(s) on ({', '.join(spec['unique'])}).")
    return out


def summarize(violations: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = [v for v in violations if v["level"] == "blocking"]
    return {"status": "FAILED" if blocking else ("WARN" if violations else "OK"), "blocking": len(blocking),
            "warnings": len(violations) - len(blocking)}
