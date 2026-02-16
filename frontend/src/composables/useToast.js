import { reactive } from 'vue'

const toasts = reactive([])
let _id = 0

/**
 * Global toast notification system.
 * Types: 'success', 'error', 'info', 'warn'
 */
export function useToast() {
  function show(message, type = 'info', duration = 4000) {
    const id = ++_id
    toasts.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }
  }

  function remove(id) {
    const idx = toasts.findIndex(t => t.id === id)
    if (idx !== -1) toasts.splice(idx, 1)
  }

  function success(msg, duration) { show(msg, 'success', duration) }
  function error(msg, duration)   { show(msg, 'error', duration ?? 6000) }
  function warn(msg, duration)    { show(msg, 'warn', duration) }
  function info(msg, duration)    { show(msg, 'info', duration) }

  return { toasts, show, remove, success, error, warn, info }
}
