/**
 * HTML-escape for v-html contexts.
 */
export function escapeHtml(s) {
  if (s == null) return ''
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * Convert DD.MM.YYYY to YYYYMMDD for proper sort ordering.
 */
export function dateSortKey(val) {
  if (!val) return ''
  const m = val.match(/^(\d{2})\.(\d{2})\.(\d{4})/)
  if (m) return m[3] + m[2] + m[1]
  return val
}

/**
 * Sort rows array by column with optional date-aware sorting.
 */
export function sortRows(rows, col, dir, dateKeys) {
  if (!col) return rows
  const d = dir === 'asc' ? 1 : -1
  const isDate = dateKeys && !!dateKeys[col]
  return rows.slice().sort((a, b) => {
    let va = a[col] == null ? '' : String(a[col])
    let vb = b[col] == null ? '' : String(b[col])
    if (isDate) {
      va = dateSortKey(va)
      vb = dateSortKey(vb)
    } else {
      va = va.toLowerCase()
      vb = vb.toLowerCase()
    }
    if (va < vb) return -1 * d
    if (va > vb) return 1 * d
    return 0
  })
}
