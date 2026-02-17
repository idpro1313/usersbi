import { useToast } from './useToast'

/**
 * Export table data to XLSX via backend.
 */
export function useExport() {
  const toast = useToast()

  async function exportToXLSX(columns, rows, filename, sheet) {
    if (!rows || !rows.length) {
      toast.warn('Нет данных для выгрузки')
      return
    }
    try {
      const token = localStorage.getItem('auth_token')
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = 'Bearer ' + token
      const r = await fetch('/api/export/table', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          columns: columns.map(c => ({ key: c.key, label: c.label })),
          rows,
          filename,
          sheet: (sheet || 'Данные').substring(0, 31),
        }),
      })
      if (!r.ok) {
        toast.error('Ошибка экспорта')
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Файл «' + filename + '» выгружен')
    } catch (e) {
      toast.error('Ошибка: ' + e.message)
    }
  }

  return { exportToXLSX }
}
