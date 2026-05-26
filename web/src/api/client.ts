import { ofetch } from 'ofetch'

export const api = ofetch.create({
  baseURL: '/api',
  onRequest({ options }) {
    const token = localStorage.getItem('access_token')
    if (token) {
      options.headers.set('Authorization', `Bearer ${token}`)
    }
  },
  onResponseError({ response }) {
    if (response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
  },
})
