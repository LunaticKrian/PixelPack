import { api } from './client'
import type { Journal } from '../types/journal'

export function listJournals(limit?: number, category?: string) {
  return api<Journal[]>('/journals', { params: { limit, category } })
}

export function createJournal(data: {
  title: string
  content?: string
  category?: string
  icon?: string
}) {
  return api<Journal>('/journals', { method: 'POST', body: data })
}

export function updateJournal(
  id: number,
  data: Partial<Pick<Journal, 'title' | 'content' | 'category' | 'icon'>>,
) {
  return api<Journal>(`/journals/${id}`, { method: 'PUT', body: data })
}

export function deleteJournal(id: number) {
  return api<void>(`/journals/${id}`, { method: 'DELETE' })
}
