import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, refreshToken as apiRefresh, getMe } from '../api/auth'
import type { User, LoginRequest, RegisterRequest } from '../types/user'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!user.value)

  async function initialize() {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      loading.value = true
      user.value = await getMe()
    } catch {
      clearTokens()
    } finally {
      loading.value = false
    }
  }

  async function login(data: LoginRequest) {
    loading.value = true
    try {
      const tokens = await apiLogin(data)
      saveTokens(tokens)
      user.value = await getMe()
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterRequest) {
    loading.value = true
    try {
      const tokens = await apiRegister(data)
      saveTokens(tokens)
      user.value = await getMe()
    } finally {
      loading.value = false
    }
  }

  async function refresh() {
    const token = localStorage.getItem('refresh_token')
    if (!token) return
    try {
      const tokens = await apiRefresh(token)
      saveTokens(tokens)
    } catch {
      clearTokens()
      user.value = null
    }
  }

  function logout() {
    clearTokens()
    user.value = null
  }

  function saveTokens(tokens: { access_token: string; refresh_token: string }) {
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }

  function clearTokens() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, loading, isAuthenticated, initialize, login, register, refresh, logout }
})
