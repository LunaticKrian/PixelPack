import { listItems, type ItemListParams } from '../api/items'

const statusLabel: Record<string, string> = {
  ACTIVE: '使用中',
  IDLE: '闲置',
  RETIRED: '退役',
  SOLD: '已售',
  DISCARDED: '已弃',
}

function escapeCSV(val: string | number | null | undefined): string {
  const s = val == null ? '' : String(val)
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"'
  }
  return s
}

export async function exportItemsCSV(params?: ItemListParams): Promise<void> {
  const headers = [
    '名称', '描述', '分类', '状态', '购买日期', '购买价格', '币种',
    '购买渠道', '当前价值', '日均成本', '总成本', '使用天数', '标签',
  ]

  const allItems: any[] = []
  let page = 1
  const pageSize = 100
  let hasMore = true

  while (hasMore) {
    const res = await listItems({ ...params, page, page_size: pageSize })
    allItems.push(...res.items)
    hasMore = page < res.pages
    page++
  }

  const rows = allItems.map(item => [
    escapeCSV(item.name),
    escapeCSV(item.description),
    escapeCSV(item.category_id),
    escapeCSV(statusLabel[item.status] || item.status),
    escapeCSV(item.purchase_date),
    escapeCSV(item.purchase_price),
    escapeCSV(item.currency),
    escapeCSV(item.purchase_channel),
    escapeCSV(item.current_value),
    escapeCSV(item.daily_cost),
    escapeCSV(item.total_cost),
    escapeCSV(item.usage_days),
    escapeCSV((item.tags || []).map((t: any) => t.name).join('|')),
  ].join(','))

  const csv = '﻿' + headers.map(escapeCSV).join(',') + '\n' + rows.join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const now = new Date()
  const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const a = document.createElement('a')
  a.href = url
  a.download = `items_${dateStr}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
