export interface Achievement {
  achievement_id: string
  name: string
  description: string
  icon: string
  exp_reward: number
  unlocked: boolean
  unlocked_at: string | null
}

export interface QuestSummary {
  level: number
  exp: number
  exp_to_next: number
  streak: number
  today_total: number
  today_completed: number
  tasks_completed_total: number
  achievements_completed: number
  achievements_total: number
  achievements: Achievement[]
}
