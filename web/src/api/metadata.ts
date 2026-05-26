import { api } from './client'
import type { Category, Tag } from '../types/item'

// Categories
export function listCategories() {
  return api<Category[]>('/categories')
}

export function createCategory(data: { name: string; icon?: string; color?: string; sort_order?: number; parent_id?: number }) {
  return api<Category>('/categories', { method: 'POST', body: data })
}

export function updateCategory(id: number, data: Partial<Category>) {
  return api<Category>(`/categories/${id}`, { method: 'PUT', body: data })
}

export function deleteCategory(id: number) {
  return api<void>(`/categories/${id}`, { method: 'DELETE' })
}

// Tags
export function listTags() {
  return api<Tag[]>('/tags')
}

export function createTag(data: { name: string; color?: string }) {
  return api<Tag>('/tags', { method: 'POST', body: data })
}

export function updateTag(id: number, data: Partial<Tag>) {
  return api<Tag>(`/tags/${id}`, { method: 'PUT', body: data })
}

export function deleteTag(id: number) {
  return api<void>(`/tags/${id}`, { method: 'DELETE' })
}
