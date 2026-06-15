# Validation False Positives — Analysis & Notes

> **Date:** 2026-06-05
> **Context:** Multi-framework end-to-end test (14 sections, GRI+IFRS+CSRD+OJK+Summary)
> **Verdict:** These are **NOT data errors**. LLM output is mathematically correct. Validator is overly strict.
> **Priority:** LOW — cosmetic fix, does not affect report quality

---

## TL;DR

Model menghitung persentase dan breakdown dari angka yang ada di DATA INPUT. Hitungannya **benar**. Tapi karena hasil hitung itu nggak ada verbatim di `source_metrics` yang dikirim ke validator, validator flag sebagai "fabricated values". Ini false positive.

---

## Issue 1: Scientific Notation Mismatch (VAL-NUM-01)

**Contoh:**
```
LLM writes:  "21,976,797.30 tCO2e"
Validator extracts: 2.19767973E7
Allowed set contains: 21976797.3 (as Python float)
Comparison: 2.19767973E7 ≠ 21976797.3 → FAIL
```

**Kenapa terjadi:**
Regex extraction dari text menghasilkan scientific notation string. Float comparison harusnya equal tapi string matching gagal.

**Apakah angkanya benar?** ✅ Ya — `21,976,797.30` = `scope3_cat15_gross_tco2e` dari Athena.

**Fix (kalau mau):** Normalize both sides ke float sebelum compare. Atau tambah `round(val, 2)` variants ke allowed set.

---

## Issue 2: LLM-Derived Percentages (VAL-NUM-01 + VAL-NUM-03)

**Contoh:**
```
Source data: scope1_natgas_tco2e = 1199.79, scope1_diesel_tco2e = 2203.20, scope1_tco2e = 3402.99
LLM writes: "Natural gas contributed 35.3% of total Scope 1 emissions"
Validator: "35.3% not in source" → FAIL
```

**Kenapa terjadi:**
LLM menghitung `1199.79 / 3402.99 × 100 = 35.24% ≈ 35.3%`. Angka ini **mathematically correct** tapi nggak ada verbatim di DATA INPUT (karena cuma totals yang dikirim, bukan percentages).

**Apakah angkanya benar?** ✅ Ya — derived correctly dari source data.

**Terkait spec DI-2:** Spec bilang "You MUST NOT perform arithmetic calculations." LLM technically melanggar ini. Tapi hasilnya akurat. Ini trade-off antara:
- Strict compliance (DI-2): Nggak output percentage → report kurang informatif
- Practical value: Include percentage → lebih readable, tapi technically "calculated"

**Fix options:**
1. Pre-compute all common percentages di aggregation layer → include di DATA INPUT
2. Add percentage ranges ke whitelist (misal: any percentage that equals `component/total × 100 ± 0.5%`)
3. Downgrade VAL-NUM-01 to WARNING for percentage values

---

## Issue 3: Table Values Not in Paragraphs (VAL-NUM-07)

**Contoh:**
```
Table contains: facility_id=FAC-0047, scope1=131.44 tCO2e
Paragraph only mentions: "Top 10 facilities contributed X tCO2e"
Validator: "Table value 131.4422 not found in paragraphs" → WARNING
```

**Kenapa terjadi:**
LLM generate detailed table (10 rows × multiple columns). Narrative text summarizes — nggak menyebut SETIAP angka dari table. Ini **normal dan expected** untuk report writing.

**Apakah angkanya benar?** ✅ Ya — values dari `scope1_by_facility` query, langsung dari Athena.

**Fix:** Downgrade VAL-NUM-07 to informational only. Atau skip check entirely — table correctness already ensured by DATA INPUT source.

---

## Issue 4: Sector-Level Data Not in Allowed Set (VAL-NUM-01)

**Contoh:**
```
Source metrics passed to validator: {scope1_tco2e: 3402.99, scope3_cat15_gross: 21976797.3, ...}
LLM writes table with sector values: "Energy Oil & Gas: 9,573,144.27 tCO2e (43.56%)"
Validator: "9573144.27 not in source" → FAIL
```

**Kenapa terjadi:**
`source_metrics` yang dikirim ke ValidationFn cuma berisi `ghg_summary` (aggregated totals). Sector-level breakdown (`pcaf_sectors`) dikirim ke SectionGenFn tapi NGGAK dikirim ke ValidationFn.

**Apakah angkanya benar?** ✅ Ya — `9,573,144.27` = `energy_oil_gas.financed_emissions_gross_tco2e` dari Athena `pcaf_by_sector` table.

**Fix:** Pass full `athena_query_result` (including `pcaf_sectors` + `scope1_facilities`) ke ValidationFn sebagai `source_metrics`. Saat ini cuma `ghg_summary` flat dict yang dikirim.

---

## Summary

| Issue | False Positive? | Data Correct? | Severity | Fix Effort |
|-------|----------------|---------------|----------|------------|
| Scientific notation | ✅ Yes | ✅ Yes | LOW | 30 min (normalize floats) |
| LLM-derived percentages | ✅ Yes | ✅ Yes | LOW | 1 hr (pre-compute or whitelist) |
| Table↔Paragraph mismatch | ✅ Yes | ✅ Yes | LOW | 15 min (downgrade to info) |
| Sector values not in allowed set | ✅ Yes | ✅ Yes | MEDIUM | 30 min (pass full data to validator) |

---

## Conclusion

Report output quality is **GOOD**. LLM correctly uses numbers from DATA INPUT and derives additional context (percentages, breakdowns) that make the report more useful. Validator needs tuning to accommodate legitimate LLM behavior while still catching actual fabrication.

**These are not bugs in the system. They are calibration issues in the validation layer.**

For demo/POC purposes: auto-approve is the correct approach. For production: implement the fixes above to reduce noise.
