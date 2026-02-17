import { ref, computed } from 'vue'

const token = ref(localStorage.getItem('auth_token') || '')
const user = ref(JSON.parse(localStorage.getItem('auth_user') || 'null'))

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const displayName = computed(() => user.value?.display_name || user.value?.username || '')

  async function login(username, password, domain) {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, domain }),
    })
    const data = await r.json().catch(() => ({}))
    if (!r.ok) {
      throw new Error(data.detail || 'Ошибка авторизации')
    }
    token.value = data.token
    user.value = data.user
    localStorage.setItem('auth_token', data.token)
    localStorage.setItem('auth_user', JSON.stringify(data.user))
    return data.user
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
  }

  async function checkAuth() {
    if (!token.value) return false
    try {
      const r = await fetch('/api/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token.value },
      })
      if (!r.ok) {
        logout()
        return false
      }
      const data = await r.json()
      user.value = {
        username: data.username,
        display_name: data.name,
        role: data.role,
        domain: data.domain,
      }
      localStorage.setItem('auth_user', JSON.stringify(user.value))
      return true
    } catch {
      logout()
      return false
    }
  }

  async function getAuthStatus() {
    try {
      const r = await fetch('/api/auth/status')
      const data = await r.json()
      return data.configured
    } catch {
      return false
    }
  }

  return { token, user, isLoggedIn, isAdmin, displayName, login, logout, checkAuth, getAuthStatus }
}
