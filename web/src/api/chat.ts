import { api } from './client'
import type { ChatMessage, ChatSession } from '../types/chat'

export function listSessions() {
  return api<ChatSession[]>('/chat/sessions')
}

export function createSession(title?: string) {
  return api<ChatSession>('/chat/sessions', { method: 'POST', body: { title: title ?? null } })
}

export function listMessages(sessionId: number) {
  return api<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)
}

export function deleteSession(sessionId: number) {
  return api<void>(`/chat/sessions/${sessionId}`, { method: 'DELETE' })
}
