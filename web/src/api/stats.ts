import { api } from './client'

export interface OverviewStats {
  total_items: number
  active_items: number
  total_assets_value: number
  avg_daily_cost: number
  total_additional_costs: number
}

export interface CategoryStat {
  category_id: number | null
  category_name: string
  item_count: number
  total_value: number
  avg_daily_cost: number
  color: string | null
}

export interface DailyCostRankItem {
  id: number
  name: string
  daily_cost: number
  purchase_price: number
  usage_days: number
  status: string
}

export interface MonthlyTrendPoint {
  month: string
  spending: number
  item_count: number
}

export interface WarrantyAlert {
  id: number
  name: string
  warranty_expiry: string
  days_remaining: number
  purchase_price: number
}

export interface RecentItem {
  id: number
  name: string
  status: string
  purchase_price: number
  daily_cost: number
  created_at: string
}

export function getOverview() {
  return api<OverviewStats>('/stats/overview')
}

export function getByCategory() {
  return api<CategoryStat[]>('/stats/by-category')
}

export function getDailyCostRank(limit = 10, status?: string) {
  return api<DailyCostRankItem[]>('/stats/daily-cost-rank', { params: { limit, status } })
}

export function getTrends(period = 'month') {
  return api<MonthlyTrendPoint[]>('/stats/trends', { params: { period } })
}

export function getWarrantyAlerts(days = 30) {
  return api<WarrantyAlert[]>('/stats/warranty-alerts', { params: { days } })
}

export function getRecentItems(limit = 5) {
  return api<RecentItem[]>('/stats/recent', { params: { limit } })
}
