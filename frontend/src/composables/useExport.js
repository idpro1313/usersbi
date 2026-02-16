/**
 * Export table data to XLSX via backend.
 */
export function useExport() {
  async function exportToXLSX(columns, rows, filename, sheet) {
    if (!rows || !rows.length) {
      alert('Нет данных для выгрузки')
      return
    }
    try {
      const r = await fetch('/api/export/table', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          columns: columns.map(c => ({ key: c.key, label: c.label })),
          rows,
          filename,
          sheet: (sheet || 'Данные').substring(0, 31),
        }),
      })
      if (!r.ok) {
        alert('Ошибка экспорта')
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
    } catch (e) {
      alert('Ошибка: ' + e.message)
    }
  }

  return { exportToXLSX }
}
