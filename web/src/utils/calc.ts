export function calcDailyCost(purchasePrice: number, additionalCosts: number, usageDays: number): number {
  const days = Math.max(1, usageDays)
  return (purchasePrice + additionalCosts) / days
}

export function calcPerUseCost(totalCost: number, usageCount: number | null): number | null {
  if (!usageCount || usageCount === 0) return null
  return totalCost / usageCount
}

export function calcUsageDays(purchaseDate: string, retiredAt: string | null): number {
  const start = new Date(purchaseDate)
  const end = retiredAt ? new Date(retiredAt) : new Date()
  return Math.max(1, Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)))
}
