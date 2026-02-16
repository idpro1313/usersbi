/**
 * Общие утилиты, используемые на всех страницах.
 * Подключается ДО page-specific скриптов.
 */
window.AppUtils = {
  API: "",

  escapeHtml: function (s) {
    if (s == null || s === undefined) return "";
    var t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  },

  /**
   * Преобразует дату DD.MM.YYYY → YYYYMMDD для правильной сортировки.
   */
  dateSortKey: function (val) {
    if (!val) return "";
    var m = val.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (m) return m[3] + m[2] + m[1];
    return val;
  },

  /**
   * Универсальная выгрузка таблицы в XLSX через POST /api/export/table.
   */
  /**
   * Fetch JSON с проверкой статуса ответа.
   */
  fetchJSON: async function (url) {
    var r = await fetch(url);
    if (!r.ok) throw new Error("Сервер вернул ошибку " + r.status);
    return r.json();
  },

  exportToXLSX: async function (columns, rows, filename, sheet) {
    if (!rows || !rows.length) { alert("Нет данных для выгрузки"); return; }
    try {
      var r = await fetch(this.API + "/api/export/table", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          columns: columns.map(function (c) { return { key: c.key, label: c.label }; }),
          rows: rows,
          filename: filename,
          sheet: (sheet || "Данные").substring(0, 31)
        })
      });
      if (!r.ok) { alert("Ошибка экспорта"); return; }
      var blob = await r.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Ошибка: " + e.message);
    }
  }
};
