import { api } from './client'
import type { Item, ItemImage, AdditionalCost } from '../types/item'
import type { PaginatedResponse } from '../types/api'

export interface ItemListParams {
  keyword?: string
  category_id?: number
  status?: string
  tag_id?: number
  sort_by?: string
  order?: string
  page?: number
  page_size?: number
}

export function listItems(params?: ItemListParams) {
  return api<PaginatedResponse<Item>>('/items', { params })
}

export function getItem(id: number) {
  return api<Item>(`/items/${id}`)
}

export function createItem(data: Partial<Item>) {
  return api<Item>('/items', { method: 'POST', body: data })
}

export function updateItem(id: number, data: Partial<Item>) {
  return api<Item>(`/items/${id}`, { method: 'PUT', body: data })
}

export function deleteItem(id: number) {
  return api<void>(`/items/${id}`, { method: 'DELETE' })
}

export function changeItemStatus(id: number, status: string, reason?: string) {
  return api<Item>(`/items/${id}/status`, { method: 'PATCH', body: { status, reason } })
}

// Additional costs
export function listCosts(itemId: number) {
  return api<AdditionalCost[]>(`/items/${itemId}/costs`)
}

export function addCost(itemId: number, data: { name: string; amount: number; date: string; description?: string }) {
  return api<AdditionalCost>(`/items/${itemId}/costs`, { method: 'POST', body: data })
}

export function updateCost(costId: number, data: Partial<AdditionalCost>) {
  return api<AdditionalCost>(`/items/costs/${costId}`, { method: 'PUT', body: data })
}

export function deleteCost(costId: number) {
  return api<void>(`/items/costs/${costId}`, { method: 'DELETE' })
}

// Images
export function uploadImage(itemId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return api<ItemImage>(`/items/${itemId}/images`, { method: 'POST', body: formData })
}

export function deleteImage(imageId: number) {
  return api<void>(`/items/images/${imageId}`, { method: 'DELETE' })
}
