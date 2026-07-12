export type TaskCategory = 'study' | 'work' | 'life' | 'health' | 'other'
export type TaskSource = 'ai' | 'manual'

export interface Task {
  id: number
  title: string
  description: string | null
  category: TaskCategory
  source: TaskSource
  target: number
  progress: number
  completed: boolean
  completed_at: string | null
  exp_reward: number
  due_date: string
  recurrence: string
  created_at: string
}

export interface TaskCompleteResult {
  task: Task
  exp_gained: number
  level: number
  leveled_up: boolean
  achievements_unlocked: string[]
}

export const CATEGORY_ICONS: Record<TaskCategory, string> = {
  study: '✎',
  work: '▦',
  life: '⌂',
  health: '✚',
  other: '◆',
}

export const CATEGORY_LABELS: Record<TaskCategory, string> = {
  study: '学习',
  work: '工作',
  life: '生活',
  health: '健康',
  other: '其他',
}

export const CATEGORY_LIST: TaskCategory[] = ['study', 'work', 'life', 'health', 'other']

/** 分类底色（与设计稿一致，非 --pixel-* 体系内、用于任务瓷砖） */
export const CATEGORY_COLORS: Record<TaskCategory, string> = {
  study: '#41a6f6',
  work: '#f5d976',
  life: '#38b764',
  health: '#ef7d57',
  other: '#b48cff',
}
