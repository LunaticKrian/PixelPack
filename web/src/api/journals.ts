import { api } from './client'
import type { Journal, Blog, BlogCreateData, BlogUpdateData } from '../types/journal'

// ── Journal (adventure log) ───────────────────────────────────────────

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

// ── Blog ──────────────────────────────────────────────────────────────

export function listBlogs(statusFilter?: string, limit?: number) {
  return api<Blog[]>('/journals/blog', { params: { status_filter: statusFilter, limit } })
}

export function createBlog(data: BlogCreateData) {
  return api<Blog>('/journals/blog', { method: 'POST', body: data })
}

export function updateBlog(id: number, data: BlogUpdateData) {
  return api<Blog>(`/journals/blog/${id}`, { method: 'PUT', body: data })
}

export function deleteBlog(id: number) {
  return api<void>(`/journals/blog/${id}`, { method: 'DELETE' })
}

export function getBlogByShareToken(token: string) {
  return api<Blog>(`/journals/blog/share/${token}`)
}
