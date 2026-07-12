export interface ChatSession {
  id: number
  title: string
  created_at: string
  updated_at: string
  last_message: string | null
  message_count: number
}

export interface ChatMessage {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  meta: Record<string, unknown> | null
  created_at: string
}

/** Agent 创建出的任务（task_created 事件携带，与 Task 部分字段一致） */
export interface CreatedTask {
  id: number
  title: string
  category: string
  exp_reward: number
  target: number
}

export type ChatStreamEvent =
  | { type: 'start' }
  | { type: 'delta'; text: string }
  | { type: 'tool'; name: string }
  | { type: 'task_created'; task: CreatedTask }
  | { type: 'done'; text: string }
  | { type: 'error'; message: string }
  | { type: 'end'; tasks_created: number }
