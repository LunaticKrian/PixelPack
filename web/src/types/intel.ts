// ── 世界地图模块 · 类型与疆域常量 ──────────────────────────────────────
// 六大疆域为前端固定常量（参见设计决策）。文章以 region slug 关联疆域。

export type RegionSlug = 'llm' | 'agent' | 'vision' | 'infra' | 'research' | 'tools'

export interface RegionDef {
  id: number
  slug: RegionSlug
  code: string // REG-01
  name: string // 大模型
  short: string // LLM
  color: string // 疆域主题色（hex）
}

/** 六大知识疆域 */
export const REGIONS: RegionDef[] = [
  { id: 1, slug: 'llm', code: 'REG-01', name: '大模型', short: 'LLM', color: '#41a6f6' },
  { id: 2, slug: 'agent', code: 'REG-02', name: '智能体', short: 'AGENT', color: '#ffd166' },
  { id: 3, slug: 'vision', code: 'REG-03', name: '视觉', short: 'VISION', color: '#73eff7' },
  { id: 4, slug: 'infra', code: 'REG-04', name: '基建', short: 'INFRA', color: '#38b764' },
  { id: 5, slug: 'research', code: 'REG-05', name: '研究', short: 'RESEARCH', color: '#b06bff' },
  { id: 6, slug: 'tools', code: 'REG-06', name: '工具', short: 'TOOLS', color: '#4ec9b0' },
]

export interface Article {
  id: number
  region: RegionSlug
  title: string
  summary: string
  body: string
  source: string
  readTime: string // '8 min'
  url?: string // 原文外链
  publishedAt: string // ISO 日期 'YYYY-MM-DD'
}

export interface IntelStats {
  todayCount: number // 今日推送
  weekCount: number // 本周累计
  archivedCount: number // 已归档
  unreadCount: number // 待读（视觉效果，= 今日未读）
}

/** 航海日志分页响应 */
export interface ArchivePage {
  items: Article[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
