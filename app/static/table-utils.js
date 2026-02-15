/**
 * Общие утилиты для таблиц с сортировкой и рендером участников.
 * Используется на страницах: Группы AD, Структура OU.
 * Подключается ПОСЛЕ utils.js.
 */
window.TableUtils = {
  /**
   * Строит простой заголовок таблицы (один ряд с сортировкой).
   */
  buildSimpleThead: function (thead, columns, onSortCallback) {
    thead.innerHTML = "";
    var tr = document.createElement("tr");
    columns.forEach(function (col) {
      var th = document.createElement("th");
      th.className = "sortable";
      th.dataset.key = col.key;
      th.innerHTML = AppUtils.escapeHtml(col.label) + " <span class=\"sort-icon\"></span>";
      th.onclick = function () { onSortCallback(col.key); };
      tr.appendChild(th);
    });
    thead.appendChild(tr);
  },

  /**
   * Обновляет иконки сортировки в заголовке.
   */
  updateSortIcons: function (thead, sortCol, sortDir) {
    var ths = thead.querySelectorAll("th[data-key]");
    for (var i = 0; i < ths.length; i++) {
      var icon = ths[i].querySelector(".sort-icon");
      if (!icon) continue;
      icon.textContent = ths[i].dataset.key === sortCol ? (sortDir === "asc" ? " \u25B2" : " \u25BC") : "";
    }
  },

  /**
   * Сортирует массив строк с учётом дат.
   */
  sortRows: function (rows, sortCol, sortDir, dateKeys) {
    if (!sortCol) return rows;
    var dir = sortDir === "asc" ? 1 : -1;
    var isDate = dateKeys && !!dateKeys[sortCol];
    return rows.slice().sort(function (a, b) {
      var va = a[sortCol] == null ? "" : String(a[sortCol]);
      var vb = b[sortCol] == null ? "" : String(b[sortCol]);
      if (isDate) {
        va = AppUtils.dateSortKey(va);
        vb = AppUtils.dateSortKey(vb);
      } else {
        va = va.toLowerCase();
        vb = vb.toLowerCase();
      }
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  },

  /**
   * Рендерит таблицу участников (groups / structure).
   */
  renderMembersTable: function (tbody, rows, columns, emptyMessage) {
    if (!rows.length) {
      tbody.innerHTML = "<tr><td colspan=\"" + columns.length + "\" class=\"muted-text\">"
        + (emptyMessage || "Нет данных") + "</td></tr>";
      return;
    }
    var esc = AppUtils.escapeHtml;
    tbody.innerHTML = rows.map(function (row) {
      var inactive = row.enabled === "Нет";
      var cls = inactive ? " class=\"uz-inactive\"" : "";
      var cells = columns.map(function (col) {
        return "<td>" + esc(row[col.key]) + "</td>";
      }).join("");
      return "<tr" + cls + ">" + cells + "</tr>";
    }).join("");
  }
};
