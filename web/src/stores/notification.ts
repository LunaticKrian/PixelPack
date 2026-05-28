import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
}

let nextId = 0

export const useNotifyStore = defineStore('notify', () => {
  const toasts = ref<Toast[]>([])
  const MAX_TOASTS = 5

  function add(type: Toast['type'], message: string, duration = 3000) {
    const id = nextId++
    toasts.value.push({ id, type, message })
    if (toasts.value.length > MAX_TOASTS) {
      toasts.value.shift()
    }
    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id: number) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx >= 0) toasts.value.splice(idx, 1)
  }

  function success(msg: string) { add('success', msg) }
  function error(msg: string) { add('error', msg, 5000) }
  function warning(msg: string) { add('warning', msg) }
  function info(msg: string) { add('info', msg) }

  return { toasts, add, remove, success, error, warning, info }
})
