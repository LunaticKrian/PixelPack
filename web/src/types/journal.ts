export interface Journal {
  id: number
  user_id: number
  type: 'system' | 'manual' | 'blog'
  category: string
  icon: string
  title: string
  content: string | null
  created_at: string
}

export interface Blog {
  id: number
  user_id: number
  type: string
  category: string
  icon: string
  title: string
  content: string | null
  cover_url: string | null
  summary: string | null
  status: 'draft' | 'published'
  share_token: string | null
  tags: string[]
  created_at: string
}

export interface BlogCreateData {
  title: string
  content?: string
  summary?: string
  cover_url?: string
  tags?: string[]
  status?: 'draft' | 'published'
}

export interface BlogUpdateData {
  title?: string
  content?: string
  summary?: string
  cover_url?: string
  tags?: string[]
  status?: 'draft' | 'published'
}
