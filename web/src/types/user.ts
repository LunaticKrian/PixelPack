export interface User {
  id: number
  username: string
  email: string | null
  avatar_url: string | null
  character_name: string | null
  portrait_url: string | null
  character_class: string | null
  birthday: string | null
  profile_completed: boolean
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
}

export interface UserUpdate {
  email?: string
  avatar_url?: string
}

export interface ProfileUpdate {
  character_name?: string
  character_class?: string
  birthday?: string
}
