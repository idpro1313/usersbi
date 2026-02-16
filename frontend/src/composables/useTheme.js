import { ref, watchEffect } from 'vue'

const STORAGE_KEY = 'app-theme'
const mode = ref(localStorage.getItem(STORAGE_KEY) || 'auto')

function applyTheme(m) {
  const html = document.documentElement
  html.removeAttribute('data-theme')
  if (m === 'light' || m === 'dark') {
    html.setAttribute('data-theme', m)
  }
}

watchEffect(() => applyTheme(mode.value))

/**
 * Theme composable: light / dark / auto.
 */
export function useTheme() {
  function setTheme(m) {
    mode.value = m
    localStorage.setItem(STORAGE_KEY, m)
  }

  function cycle() {
    const order = ['auto', 'light', 'dark']
    const idx = order.indexOf(mode.value)
    setTheme(order[(idx + 1) % order.length])
  }

  return { mode, setTheme, cycle }
}
