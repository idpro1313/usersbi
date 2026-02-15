(function () {
  var API = "";
  var CHUNK = 200; // строк за одну подгрузку

  // ─── Определение колонок таблицы ───
  var COLUMNS = [
    { key: "source",             label: "Источник" },
    { key: "login",              label: "Логин" },
    { key: "domain",             label: "Домен" },
    { key: "uz_active",          label: "УЗ активна" },
    { key: "password_last_set",  label: "Пароль" },
    { key: "account_expires",    label: "Срок УЗ" },
    { key: "staff_uuid",         label: "StaffUUID" },
    { key: "mfa_enabled",        label: "MFA" },
    { key: "mfa_created_at",     label: "MFA с" },
    { key: "mfa_last_login",     label: "Вход MFA" },
    { key: "mfa_authenticators", label: "Способ" },
    { key: "fio_ad",             label: "ФИО (AD)" },
    { key: "fio_mfa",            label: "ФИО (MFA)" },
    { key: "fio_people",         label: "ФИО (Кадры)" },
    { key: "email_ad",           label: "Email (AD)" },
    { key: "email_mfa",          label: "Email (MFA)" },
    { key: "email_people",       label: "Email (Кадры)" },
    { key: "phone_ad",           label: "Тел. (AD)" },
    { key: "mobile_ad",          label: "Моб. (AD)" },
    { key: "phone_mfa",          label: "Тел. (MFA)" },
    { key: "phone_people",       label: "Тел. (Кадры)" },
    { key: "discrepancies",      label: "Расхождения" }
  ];

  // Общее кол-во колонок включая "#"
  var TOTAL_COLS = COLUMNS.length + 1;

  // ─── Состояние ───
  var cachedRows = [];
  var filteredRows = [];  // отфильтрованные + отсортированные
  var renderedCount = 0;  // сколько строк уже в DOM
  var sortCol = null;
  var sortDir = "asc";
  var colFilters = {};

  // ─── DOM ───
  var thead = document.getElementById("thead");
  var tbody = document.getElementById("tbody");
  var tableContainer = document.querySelector(".table-container");
  var tableFooter = document.getElementById("table-footer");
  var filterInput = document.getElementById("filter");
  var btnRefresh = document.getElementById("btn-refresh");

  // ─── Утилиты ───
  function escapeHtml(s) {
    if (s == null || s === undefined) return "";
    var t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  }

  // Колонки с датами (для корректной сортировки)
  var DATE_KEYS = {
    "password_last_set": true,
    "account_expires": true,
    "mfa_created_at": true,
    "mfa_last_login": true
  };

  /**
   * Преобразует дату DD.MM.YYYY → YYYYMMDD для правильной сортировки.
   * Если формат не распознан — возвращает исходную строку.
   */
  function dateSortKey(val) {
    if (!val) return "";
    var m = val.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (m) return m[3] + m[2] + m[1]; // YYYYMMDD
    return val;
  }

  function rowClass(source) {
    if (!source) return "";
    if (source.indexOf("AD") === 0) return "source-ad";
    if (source === "MFA") return "source-mfa";
    if (source === "Кадры") return "source-people";
    return "";
  }

  // ─── Генерация заголовков ───
  function buildThead() {
    thead.innerHTML = "";

    // Ряд 1: метки + сортировка
    var trLabels = document.createElement("tr");
    trLabels.className = "thead-labels";

    // Колонка "#"
    var thNum = document.createElement("th");
    thNum.className = "col-num";
    thNum.textContent = "#";
    trLabels.appendChild(thNum);

    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      th.className = "sortable";
      th.dataset.key = col.key;
      th.innerHTML = escapeHtml(col.label) + " <span class=\"sort-icon\"></span>";
      th.onclick = function () { onSort(col.key); };
      trLabels.appendChild(th);
    });
    thead.appendChild(trLabels);

    // Ряд 2: фильтры
    var trFilters = document.createElement("tr");
    trFilters.className = "thead-filters";

    // Пустая ячейка под "#"
    var thNumF = document.createElement("th");
    thNumF.className = "col-num";
    trFilters.appendChild(thNumF);

    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      var sel = document.createElement("select");
      sel.className = "col-filter";
      sel.dataset.key = col.key;
      sel.addEventListener("change", function () {
        colFilters[col.key] = sel.value;
        updateFilterHighlight();
        applyFilters();
      });
      th.appendChild(sel);
      trFilters.appendChild(th);
    });
    thead.appendChild(trFilters);

    updateSortIcons();
    updateFilterOptions();
  }

  /**
   * Возвращает строки, прошедшие глобальный поиск и все колоночные фильтры,
   * КРОМЕ фильтра по колонке excludeKey (чтобы в её dropdown показать
   * все доступные варианты с учётом остальных фильтров).
   */
  function rowsFilteredExcept(excludeKey) {
    var globalFilter = (filterInput ? filterInput.value : "").trim().toLowerCase();
    var rows = cachedRows;

    if (globalFilter) {
      rows = rows.filter(function (row) {
        return JSON.stringify(row).toLowerCase().indexOf(globalFilter) !== -1;
      });
    }

    COLUMNS.forEach(function (col) {
      if (col.key === excludeKey) return;
      var f = colFilters[col.key] || "";
      if (!f) return;
      rows = rows.filter(function (row) {
        return String(row[col.key] == null ? "" : row[col.key]) === f;
      });
    });

    return rows;
  }

  function updateFilterOptions() {
    var selects = thead.querySelectorAll(".thead-filters select");
    for (var i = 0; i < selects.length; i++) {
      var sel = selects[i];
      var key = sel.dataset.key;
      var prev = colFilters[key] || "";

      // Варианты — только из строк, прошедших все ДРУГИЕ фильтры
      var available = rowsFilteredExcept(key);
      var vals = {};
      for (var j = 0; j < available.length; j++) {
        var v = available[j][key];
        if (v != null && v !== "") vals[String(v)] = true;
      }
      var isDate = !!DATE_KEYS[key];
      var sorted = Object.keys(vals).sort(function (a, b) {
        var aStub = a.indexOf("НЕТ") === 0 ? 0 : 1;
        var bStub = b.indexOf("НЕТ") === 0 ? 0 : 1;
        if (aStub !== bStub) return aStub - bStub;
        if (isDate) {
          var da = dateSortKey(a);
          var db = dateSortKey(b);
          if (da < db) return -1;
          if (da > db) return 1;
          return 0;
        }
        return a.localeCompare(b, "ru");
      });

      sel.innerHTML = "";
      var optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "\u2014 все (" + sorted.length + ")";
      sel.appendChild(optAll);

      for (var k = 0; k < sorted.length; k++) {
        var opt = document.createElement("option");
        opt.value = sorted[k];
        opt.textContent = sorted[k];
        sel.appendChild(opt);
      }

      sel.value = prev;
      if (sel.value !== prev) {
        colFilters[key] = "";
        sel.value = "";
      }
    }
    updateFilterHighlight();
  }

  function updateFilterHighlight() {
    // Подсветить заголовки столбцов с активным фильтром
    var labelThs = thead.querySelectorAll(".thead-labels th.sortable");
    for (var i = 0; i < labelThs.length; i++) {
      var key = labelThs[i].dataset.key;
      if (colFilters[key]) {
        labelThs[i].classList.add("filter-active");
      } else {
        labelThs[i].classList.remove("filter-active");
      }
    }
  }

  function updateSortIcons() {
    var ths = thead.querySelectorAll(".thead-labels th.sortable");
    for (var i = 0; i < ths.length; i++) {
      var icon = ths[i].querySelector(".sort-icon");
      var key = ths[i].dataset.key;
      if (key === sortCol) {
        icon.textContent = sortDir === "asc" ? " \u25B2" : " \u25BC";
      } else {
        icon.textContent = "";
      }
    }
  }

  function onSort(key) {
    if (sortCol === key) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortCol = key;
      sortDir = "asc";
    }
    updateSortIcons();
    applyFilters();
  }

  // ─── Фильтрация + сортировка → filteredRows ───
  function applyFilters() {
    var globalFilter = (filterInput ? filterInput.value : "").trim().toLowerCase();
    var rows = cachedRows;

    // 1) Глобальный поиск
    if (globalFilter) {
      rows = rows.filter(function (row) {
        return JSON.stringify(row).toLowerCase().indexOf(globalFilter) !== -1;
      });
    }

    // 2) Фильтры по столбцам
    COLUMNS.forEach(function (col) {
      var f = colFilters[col.key] || "";
      if (!f) return;
      rows = rows.filter(function (row) {
        return String(row[col.key] == null ? "" : row[col.key]) === f;
      });
    });

    // 3) Сортировка
    if (sortCol) {
      var dir = sortDir === "asc" ? 1 : -1;
      var isDate = !!DATE_KEYS[sortCol];
      rows = rows.slice().sort(function (a, b) {
        var va = a[sortCol] == null ? "" : String(a[sortCol]);
        var vb = b[sortCol] == null ? "" : String(b[sortCol]);
        if (isDate) {
          va = dateSortKey(va);
          vb = dateSortKey(vb);
        } else {
          va = va.toLowerCase();
          vb = vb.toLowerCase();
        }
        if (va < vb) return -1 * dir;
        if (va > vb) return  1 * dir;
        return 0;
      });
    }

    filteredRows = rows;
    renderedCount = 0;
    tbody.innerHTML = "";
    renderChunk();
    updateFooter();
    updateFilterOptions();
  }

  // ─── Подгрузка порции строк ───
  function renderChunk() {
    var end = Math.min(renderedCount + CHUNK, filteredRows.length);
    if (renderedCount >= end) return;

    var fragment = document.createDocumentFragment();

    for (var i = renderedCount; i < end; i++) {
      var row = filteredRows[i];
      var tr = document.createElement("tr");
      var inactive = row.uz_active === "Нет";
      tr.className = rowClass(row.source) + (inactive ? " uz-inactive" : "");

      // Ячейка "#"
      var tdNum = document.createElement("td");
      tdNum.className = "col-num";
      tdNum.textContent = i + 1;
      tr.appendChild(tdNum);

      // Ячейки данных
      for (var j = 0; j < COLUMNS.length; j++) {
        var col = COLUMNS[j];
        var td = document.createElement("td");
        if (col.key === "discrepancies") td.className = "discrepancy";
        td.textContent = row[col.key] == null ? "" : row[col.key];
        tr.appendChild(td);
      }

      fragment.appendChild(tr);
    }

    tbody.appendChild(fragment);
    renderedCount = end;
    updateFooter();
  }

  function updateFooter() {
    var total = cachedRows.length;
    var filtered = filteredRows.length;
    var shown = renderedCount;
    var parts = ["Всего: " + total];
    if (filtered < total) parts.push("найдено: " + filtered);
    if (shown < filtered) parts.push("показано: " + shown);
    tableFooter.textContent = parts.join(" · ");
  }

  // ─── Подгрузка при прокрутке ───
  if (tableContainer) {
    tableContainer.addEventListener("scroll", function () {
      if (renderedCount >= filteredRows.length) return;
      var el = tableContainer;
      // Когда до конца осталось менее 300px — подгружаем
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
        renderChunk();
      }
    });
  }

  // ─── Загрузка данных ───
  async function loadTable() {
    tbody.innerHTML = "<tr><td colspan=\"" + TOTAL_COLS + "\">Загрузка…</td></tr>";
    try {
      var r = await fetch(API + "/api/consolidated");
      var data = await r.json();
      cachedRows = data.rows || [];
      updateFilterOptions();
      applyFilters();
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + TOTAL_COLS + "\">Ошибка загрузки: " + escapeHtml(e.message) + "</td></tr>";
      tableFooter.textContent = "";
    }
  }

  btnRefresh.onclick = loadTable;
  if (filterInput) {
    filterInput.addEventListener("input", function () { applyFilters(); });
  }

  // ─── Экспорт XLSX (с учётом фильтров) ───
  var btnExport = document.getElementById("btn-export");
  if (btnExport) {
    btnExport.onclick = async function () {
      var dataToExport = filteredRows.length ? filteredRows : cachedRows;
      if (!dataToExport.length) { alert("Нет данных для выгрузки"); return; }
      try {
        var r = await fetch(API + "/api/export/table", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            columns: COLUMNS.map(function (c) { return { key: c.key, label: c.label }; }),
            rows: dataToExport,
            filename: "Svodka_AD_MFA_People.xlsx",
            sheet: "Сводная"
          })
        });
        if (!r.ok) { alert("Ошибка экспорта"); return; }
        var blob = await r.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "Svodka_AD_MFA_People.xlsx";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (e) {
        alert("Ошибка: " + e.message);
      }
    };
  }

  // ─── Инициализация ───
  buildThead();
  loadTable();
})();
