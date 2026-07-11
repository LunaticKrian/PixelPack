// ── 世界地图模块 · API 层 ────────────────────────────────────────────
// 直连后端 /api/intel/*（ofetch 实例自带 baseURL=/api 与 JWT 注入）。
// 三个函数签名与原 Mock 完全一致，WorldMap.vue 无需改动。

import { api } from './client'
import type { ArchivePage, Article, GenerateResult, IntelStats, RegionSlug } from '../types/intel'

/** 今日推送（信号台） */
export function listTodayIntel(): Promise<Article[]> {
  return api<Article[]>('/intel/today')
}

/** 历史归档（航海日志），一天一页 + 可选疆域筛选。page 从 1 起。 */
export function listArchive(region?: RegionSlug | null, page: number = 1): Promise<ArchivePage> {
  return api<ArchivePage>('/intel/archive', {
    params: { page, ...(region ? { region } : {}) },
  })
}

/** 顶部统计 */
export function getIntelStats(): Promise<IntelStats> {
  return api<IntelStats>('/intel/stats')
}

/** 主动发起侦测：触发 Agent 抓取今日情报（overwrite=true 刷新今日）。
 * Agent 含 RSS 抓取 + 阅读，实测约 2-3 分钟，超时设 5 分钟。 */
export function generateIntel(overwrite: boolean = true): Promise<GenerateResult> {
  return api<GenerateResult>('/intel/generate', {
    method: 'POST',
    params: { overwrite },
    timeout: 300000,
  })
}
