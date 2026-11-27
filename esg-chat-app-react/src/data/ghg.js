// GHG inventory structured like the GHG Protocol Scope 3 reporting template
// (Part 1 descriptive · Part 2 emissions · Part 3 biogenic · Part 4 methodology · Part 5 base year · Part 6 optional)
// All numbers are synthetic for the fictional Bank Nusantara Sejahtera.
import { BANK } from './bank'

export const PART1 = [
  ['Company name', BANK.name],
  ['Description of the company', 'Indonesian universal bank with retail, commercial, Sharia, multifinance and securities subsidiaries.'],
  ['Consolidation approach', 'Operational control'],
  ['Organizational boundary', 'BNS Bank, BNS Syariah, BNS Finance and BNS Sekuritas; 842 branches and 4 head-office buildings.'],
  ['Reporting period', '1 Jan – 31 Dec 2025'],
  ['Scope 3 activities included', 'Categories 1, 2, 3, 4, 5, 6, 7 and 15 (investments / financed emissions).'],
  ['Activities excluded (with justification)', 'Categories 8-14 excluded: not relevant to a bank (no upstream leased assets under operational control, no physical products sold, no franchises).'],
  ['Base year and rationale', '2022. First year with complete facility-level energy data and a full PCAF-aligned loan book.'],
  ['Base-year recalculation policy', 'Recalculate when structural changes or methodology changes alter emissions by more than 5%. Recalculated once in 2024 (new grid emission factors).'],
]

// Part 2 — rows: key, label, group, value (tCO2e), baseYear, included
export const PART2 = [
  { k: 's1', label: 'Scope 1 · Direct emissions', group: 'Scope 1', v: BANK.scope1, base: 13900, inc: true },
  { k: 's2', label: 'Scope 2 · Purchased electricity (location-based)', group: 'Scope 2', v: BANK.scope2Location, base: 44100, inc: true },
  { k: 'c1', label: 'Cat 1 · Purchased goods and services', group: 'Upstream', v: 18200, base: 19800, inc: true },
  { k: 'c2', label: 'Cat 2 · Capital goods', group: 'Upstream', v: 6400, base: 7100, inc: true },
  { k: 'c3', label: 'Cat 3 · Fuel- and energy-related activities', group: 'Upstream', v: 7900, base: 8600, inc: true },
  { k: 'c4', label: 'Cat 4 · Upstream transportation and distribution', group: 'Upstream', v: 1150, base: 1300, inc: true },
  { k: 'c5', label: 'Cat 5 · Waste generated in operations', group: 'Upstream', v: 640, base: 720, inc: true },
  { k: 'c6', label: 'Cat 6 · Business travel', group: 'Upstream', v: 4300, base: 3900, inc: true },
  { k: 'c7', label: 'Cat 7 · Employee commuting', group: 'Upstream', v: 9800, base: 10400, inc: true },
  { k: 'c8', label: 'Cat 8 · Upstream leased assets', group: 'Upstream', v: null, base: null, inc: false },
  { k: 'c9', label: 'Cat 9 · Downstream transportation and distribution', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c10', label: 'Cat 10 · Processing of sold products', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c11', label: 'Cat 11 · Use of sold products', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c12', label: 'Cat 12 · End-of-life treatment of sold products', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c13', label: 'Cat 13 · Downstream leased assets', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c14', label: 'Cat 14 · Franchises', group: 'Downstream', v: null, base: null, inc: false },
  { k: 'c15', label: 'Cat 15 · Investments (financed emissions)', group: 'Downstream', v: BANK.scope3Cat15, base: 6050000, inc: true },
]

// gases: [CO2 t, CH4 tCO2e, N2O tCO2e, HFCs tCO2e, PFCs tCO2e, SF6 tCO2e]
export const GASES = [
  { scope: 'Scope 1', vals: [11900, 140, 190, 250, 0, 0] },
  { scope: 'Scope 2', vals: [38100, 360, 490, 0, 0, 0] },
]
export const GAS_NAMES = ['CO2', 'CH4', 'N2O', 'HFCs', 'PFCs', 'SF6']

export const PART3 = { note: 'Biogenic CO2 not material: no biomass combustion in owned operations. Reported as 0 for all categories.', total: 0 }

export const PART4 = [
  { scope: 'Scope 1', method: 'GHG Protocol Corporate Standard; fuel activity data × emission factors (Indonesian MEMR/IPCC); refrigerant top-ups for HFCs.', data: 'Generator diesel, natural gas, refrigerant logs from 846 facilities.', quality: 'Score 1-2 (metered / invoiced)', supplier: 0 },
  { scope: 'Scope 2', method: 'GHG Protocol Scope 2 Guidance; location-based with regional grid factors, market-based with REC adjustment.', data: 'Monthly utility kWh via Energy API; PLN bills for legacy sites.', quality: 'Score 1-3, 4% months imputed', supplier: 100 },
  { scope: 'Cat 1 · Purchased goods', method: 'Spend-based using EEIO factors.', data: 'Procurement ledger spend by category.', quality: 'Low (spend-based)', supplier: 0 },
  { scope: 'Cat 2 · Capital goods', method: 'Spend-based using EEIO factors.', data: 'Fixed-asset additions.', quality: 'Low (spend-based)', supplier: 0 },
  { scope: 'Cat 3 · Fuel & energy', method: 'Average-data: upstream factors × Scope 1/2 energy.', data: 'Scope 1 and Scope 2 energy volumes.', quality: 'Medium', supplier: 0 },
  { scope: 'Cat 6 · Business travel', method: 'Distance-based per travel mode.', data: 'Travel agency export.', quality: 'Medium', supplier: 35 },
  { scope: 'Cat 7 · Commuting', method: 'Average-data using HR headcount and survey.', data: 'HR headcount by location; commute survey (62% response).', quality: 'Medium', supplier: 0 },
  { scope: 'Cat 15 · Investments', method: 'PCAF Global GHG Accounting Standard Part A; attribution factor = outstanding / (EVIC or total equity + debt).', data: 'Loan book from Core Banking; borrower emissions where reported, else PCAF sector averages.', quality: 'Weighted PCAF score 3.4 (5 asset classes)', supplier: 46 },
]

export const BASE_YEAR = 2022

export const PART6 = [
  ['Emissions subdivided by business unit / facility', true],
  ['Scope 3 disaggregated within categories', true],
  ['Emissions by individual gas', true],
  ['Other GHGs with IPCC GWP (e.g. NF3, CFCs)', false],
  ['Historic vs future scope 3 emissions', false],
  ['Qualitative information on unquantified sources', true],
  ['GHG removals / sequestration (separate)', false],
  ['Project-based reductions (separate)', false],
  ['Quantitative data quality assessment', true],
  ['Inventory uncertainty and quality-improvement policy', true],
  ['Type of assurance and assurer opinion', false],
  ['Intensity ratios and performance indicators', true],
  ['GHG management and reduction activities / targets', true],
  ['Supplier / partner engagement information', false],
  ['Benchmark comparison with external peers', true],
  ['Purchases of GHG reduction instruments / offsets', false],
  ['Contractual provisions on GHG risks or obligations', false],
  ['Causes of changes that did not trigger base-year recalculation', true],
  ['Emissions for all years between base year and reporting year', true],
  ['Additional explanations for context', true],
]

export const TREND = [
  { year: 2022, s12: 58000, fin: 6050000 },
  { year: 2023, s12: 56200, fin: 5880000 },
  { year: 2024, s12: 53400, fin: 5640000 },
  { year: 2025, s12: BANK.scope1 + BANK.scope2Location, fin: BANK.scope3Cat15 },
]

export const totals = () => {
  const inc = PART2.filter((r) => r.inc)
  const total = inc.reduce((a, r) => a + r.v, 0)
  const baseTotal = inc.reduce((a, r) => a + r.base, 0)
  const ops = inc.filter((r) => r.k !== 'c15').reduce((a, r) => a + r.v, 0)
  return { total, baseTotal, ops, fin: BANK.scope3Cat15, finShare: (BANK.scope3Cat15 / total) * 100, change: ((total - baseTotal) / baseTotal) * 100 }
}

export const part6Coverage = () => Math.round((PART6.filter((p) => p[1]).length / PART6.length) * 100)
