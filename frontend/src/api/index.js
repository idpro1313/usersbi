/**
 * API-модуль с Bearer-авторизацией и обработкой 401.
 */

function authHeaders() {
  const token = localStorage.getItem('auth_token')
  const h = {}
  if (token) h['Authorization'] = 'Bearer ' + token
  return h
}

function handle401(r) {
  if (r.status === 401) {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }
}

/**
 * Fetch JSON with status check.
 */
export async function fetchJSON(url) {
  const r = await fetch(url, { headers: authHeaders() })
  handle401(r)
  if (!r.ok) {
    const data = await r.json().catch(() => ({}))
    throw new Error(data.detail || 'Сервер вернул ошибку ' + r.status)
  }
  return r.json()
}

/**
 * POST JSON and return parsed response.
 */
export async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  handle401(r)
  if (!r.ok) {
    const data = await r.json().catch(() => ({}))
    throw new Error(data.detail || 'Ошибка сервера ' + r.status)
  }
  return r.json()
}

/**
 * PUT JSON.
 */
export async function putJSON(url, body) {
  const r = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  handle401(r)
  if (!r.ok) {
    const data = await r.json().catch(() => ({}))
    throw new Error(data.detail || 'Ошибка сервера ' + r.status)
  }
  return r.json()
}

/**
 * POST FormData (file upload).
 */
export async function postForm(url, formData) {
  const r = await fetch(url, { method: 'POST', body: formData, headers: authHeaders() })
  handle401(r)
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Ошибка загрузки')
  return data
}

/**
 * DELETE request.
 */
export async function del(url) {
  const r = await fetch(url, { method: 'DELETE', headers: authHeaders() })
  handle401(r)
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Ошибка удаления')
  return data
}
