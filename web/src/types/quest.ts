export interface DailyQuest {
  id: number
  quest_key: string
  name: string
  description: string
  target: number
  progress: number
  completed: boolean
  exp_reward: number
}

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
  daily_quests: DailyQuest[]
  achievements: Achievement[]
  level: number
  total_exp: number
  achievements_completed: number
  achievements_total: number
}
