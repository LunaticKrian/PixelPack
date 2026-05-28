import { api } from './client'
import type { DailyQuest, Achievement, QuestSummary } from '../types/quest'

export function getDailyQuests() {
  return api<DailyQuest[]>('/quests/daily')
}

export function reportProgress(quest_key: string, increment = 1) {
  return api<{ quest_completed: boolean; achievements_unlocked: string[] }>('/quests/progress', {
    method: 'POST',
    body: { quest_key, increment },
  })
}

export function getAchievements() {
  return api<Achievement[]>('/quests/achievements')
}

export function getQuestSummary() {
  return api<QuestSummary>('/quests/summary')
}
