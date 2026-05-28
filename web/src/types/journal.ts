export interface Journal {
  id: number
  user_id: number
  type: 'system' | 'manual'
  category: string
  icon: string
  title: string
  content: string | null
  created_at: string
}
