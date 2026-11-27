// Fictional bank used for the JPS demo. All figures are synthetic.
export const BANK = {
  name: 'Bank Nusantara Sejahtera',
  short: 'BNS',
  fy: 'FY2025',
  // GHG inventory (tCO2e), synthetic
  scope1: 12480,
  scope2Location: 38950,
  scope2Market: 31200,
  scope3Cat15: 5420000,
  totalLoansIdrTn: 520,
}

export const SUBSIDIARIES = [
  { id: 'bank', name: 'BNS Bank', short: 'Bank', weight: 1.0, budget: 1400, color: '#4f8cf7' },
  { id: 'syariah', name: 'BNS Syariah', short: 'Syariah', weight: 0.45, budget: 700, color: '#06d6a0' },
  { id: 'finance', name: 'BNS Finance', short: 'Finance', weight: 0.35, budget: 520, color: '#7c5cfc' },
  { id: 'sekuritas', name: 'BNS Sekuritas', short: 'Sekuritas', weight: 0.2, budget: 300, color: '#fbbf24' },
]

export const totalGhg = () => BANK.scope1 + BANK.scope2Location + BANK.scope3Cat15
export const financedShare = () => (BANK.scope3Cat15 / totalGhg()) * 100
