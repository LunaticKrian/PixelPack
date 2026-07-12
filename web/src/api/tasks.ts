import { api } from './client'
import type { Task, TaskCompleteResult, TaskCategory } from '../types/task'

export interface TaskCreateInput {
  title: string
  description?: string
  category?: TaskCategory
  target?: number
  exp_reward?: number
  due_date?: string
  recurrence?: 'once' | 'daily' | 'weekly'
}

export interface TaskUpdateInput extends Partial<TaskCreateInput> {}

export function listTasks(date?: string) {
  return api<Task[]>('/tasks', { params: date ? { date } : {} })
}

export function createTask(body: TaskCreateInput) {
  return api<Task>('/tasks', { method: 'POST', body })
}

export function updateTask(id: number, body: TaskUpdateInput) {
  return api<Task>(`/tasks/${id}`, { method: 'PATCH', body })
}

export function deleteTask(id: number) {
  return api<void>(`/tasks/${id}`, { method: 'DELETE' })
}

export function completeTask(id: number) {
  return api<TaskCompleteResult>(`/tasks/${id}/complete`, { method: 'POST' })
}

export function uncompleteTask(id: number) {
  return api<Task>(`/tasks/${id}/uncomplete`, { method: 'POST' })
}

export function progressTask(id: number, increment = 1) {
  return api<Task>(`/tasks/${id}/progress`, { method: 'POST', body: { increment } })
}
