import { api } from './client'
import type { LoginRequest, ProfileUpdate, RegisterRequest, TokenResponse, User, UserUpdate, PasswordChange } from '../types/user'

export function login(data: LoginRequest) {
  return api<TokenResponse>('/auth/login', { method: 'POST', body: data })
}

export function register(data: RegisterRequest) {
  return api<TokenResponse>('/auth/register', { method: 'POST', body: data })
}

export function refreshToken(refresh_token: string) {
  return api<TokenResponse>('/auth/refresh', { method: 'POST', body: { refresh_token } })
}

export function getMe() {
  return api<User>('/auth/me')
}

export function updateMe(data: UserUpdate) {
  return api<User>('/auth/me', { method: 'PUT', body: data })
}

export function changePassword(data: PasswordChange) {
  return api<{ message: string }>('/auth/password', { method: 'PUT', body: data })
}

export function updateProfile(data: ProfileUpdate) {
  return api<User>('/auth/profile', { method: 'PUT', body: data })
}

export function uploadPortrait(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return api<{ url: string }>('/auth/portrait', { method: 'POST', body: formData })
}
