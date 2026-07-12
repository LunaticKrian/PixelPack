import { api } from './client'
import type { Achievement, QuestSummary } from '../types/quest'

export function getQuestSummary() {
  return api<QuestSummary>('/quests/summary')
}

export function getAchievements() {
  return api<Achievement[]>('/quests/achievements')
}
