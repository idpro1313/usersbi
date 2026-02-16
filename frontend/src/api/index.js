/**
 * Fetch JSON with status check.
 */
export async function fetchJSON(url) {
  const r = await fetch(url)
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
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
  const r = await fetch(url, { method: 'POST', body: formData })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Ошибка загрузки')
  return data
}

/**
 * DELETE request.
 */
export async function del(url) {
  const r = await fetch(url, { method: 'DELETE' })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Ошибка удаления')
  return data
}
