import { ofetch } from 'ofetch'

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const rt = localStorage.getItem('refresh_token')
  if (!rt) return false

  try {
    const res = await ofetch<{ access_token: string; refresh_token: string }>('/api/auth/refresh', {
      method: 'POST',
      body: { refresh_token: rt },
    })
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    return true
  } catch {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    return false
  }
}

export const api = ofetch.create({
  baseURL: '/api',
  onRequest({ options }) {
    const token = localStorage.getItem('access_token')
    if (token) {
      options.headers.set('Authorization', `Bearer ${token}`)
    }
  },
  async onResponseError({ response, options, request }) {
    if (response.status !== 401) return

    // Don't retry for auth endpoints themselves
    const url = typeof request === 'string' ? request : request.toString()
    if (url.includes('/auth/login') || url.includes('/auth/register') || url.includes('/auth/refresh')) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      return
    }

    // Deduplicate concurrent refreshes
    if (!refreshPromise) {
      refreshPromise = tryRefresh()
    }
    const refreshed = await refreshPromise
    refreshPromise = null

    if (!refreshed) {
      window.location.href = '/login'
      return
    }

    // Retry the original request with the new token
    const newToken = localStorage.getItem('access_token')
    if (newToken) {
      options.headers.set('Authorization', `Bearer ${newToken}`)
    }
    return api(request, options)
  },
})
