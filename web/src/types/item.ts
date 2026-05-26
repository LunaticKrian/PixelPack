export type ItemStatus = 'ACTIVE' | 'IDLE' | 'RETIRED' | 'SOLD' | 'DISCARDED'

export interface Item {
  id: number
  name: string
  description: string | null
  category_id: number | null
  status: ItemStatus
  purchase_date: string
  purchase_price: number
  currency: string
  purchase_channel: string | null
  current_value: number | null
  warranty_expiry: string | null
  expected_lifespan: number | null
  usage_count: number | null
  retired_at: string | null
  retired_reason: string | null
  created_at: string
  updated_at: string
  // computed fields from backend
  daily_cost: number
  per_use_cost: number | null
  total_cost: number
  usage_days: number
  // relations (populated by backend)
  images: ItemImage[]
  tags: Tag[]
  additional_costs: AdditionalCost[]
}

export interface ItemImage {
  id: number
  item_id: number
  url: string
  sort_order: number
  created_at: string
}

export interface AdditionalCost {
  id: number
  item_id: number
  name: string
  amount: number
  date: string
  description: string | null
}

export interface Category {
  id: number
  name: string
  icon: string | null
  color: string | null
  sort_order: number
  parent_id: number | null
}

export interface Tag {
  id: number
  name: string
  color: string
}
