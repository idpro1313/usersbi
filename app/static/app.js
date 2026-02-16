(function () {
  var API = AppUtils.API;
  var esc = AppUtils.escapeHtml;
  var CHUNK = 200;

  // ─── Колонки таблицы ───
  var COLUMNS = [
    { key: "source",             label: "Источник" },
    { key: "account_type",       label: "Тип УЗ" },
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

  var TOTAL_COLS = COLUMNS.length + 1;

  var DATE_KEYS = {
    "password_last_set": true, "account_expires": true,
    "mfa_created_at": true, "mfa_last_login": true
  };

  // ─── Состояние ───
  var cachedRows = [];
  var filteredRows = [];
  var renderedCount = 0;
  var sortCol = null;
  var sortDir = "asc";
  var colFilters = {};
  var searchCache = new Map();  // Кэш строк для глобального поиска

  // ─── DOM ───
  var thead = document.getElementById("thead");
  var tbody = document.getElementById("tbody");
  var tableContainer = document.querySelector(".table-container");
  var tableFooter = document.getElementById("table-footer");
  var filterInput = document.getElementById("filter");
  var btnRefresh = document.getElementById("btn-refresh");

  // ─── Утилиты ───
  function rowClass(source) {
    if (!source) return "";
    if (source.indexOf("AD") === 0) return "source-ad";
    if (source === "MFA") return "source-mfa";
    if (source === "Кадры") return "source-people";
    return "";
  }

  /**
   * Строит кэшированную строку для глобального поиска (один раз на запись).
   */
  function getSearchString(row) {
    var cached = searchCache.get(row);
    if (cached !== undefined) return cached;
    var parts = [];
    for (var i = 0; i < COLUMNS.length; i++) {
      var v = row[COLUMNS[i].key];
      if (v != null && v !== "") parts.push(String(v));
    }
    var str = parts.join(" ").toLowerCase();
    searchCache.set(row, str);
    return str;
  }

  // ─── Заголовки ───
  function buildThead() {
    thead.innerHTML = "";

    // Ряд 1: метки + сортировка
    var trLabels = document.createElement("tr");
    trLabels.className = "thead-labels";
    var thNum = document.createElement("th");
    thNum.className = "col-num";
    thNum.textContent = "#";
    trLabels.appendChild(thNum);

    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      th.className = "sortable";
      th.dataset.key = col.key;
      th.innerHTML = esc(col.label) + " <span class=\"sort-icon\"></span>";
      th.onclick = function () { onSort(col.key); };
      trLabels.appendChild(th);
    });
    thead.appendChild(trLabels);

    // Ряд 2: фильтры
    var trFilters = document.createElement("tr");
    trFilters.className = "thead-filters";
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
   * Каскадные фильтры: строки, прошедшие все фильтры КРОМЕ excludeKey.
   */
  function rowsFilteredExcept(excludeKey) {
    var globalFilter = (filterInput ? filterInput.value : "").trim().toLowerCase();
    var rows = cachedRows;

    if (globalFilter) {
      rows = rows.filter(function (row) {
        return getSearchString(row).indexOf(globalFilter) !== -1;
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
          var da = AppUtils.dateSortKey(a);
          var db2 = AppUtils.dateSortKey(b);
          if (da < db2) return -1;
          if (da > db2) return 1;
          return 0;
        }
        return a.localeCompare(b, "ru");
      });

      // DocumentFragment для батчевой вставки
      var fragment = document.createDocumentFragment();
      var optAll = document.createElement("option");
      optAll.value = "";
      optAll.textContent = "\u2014 все (" + sorted.length + ")";
      fragment.appendChild(optAll);

      for (var k = 0; k < sorted.length; k++) {
        var opt = document.createElement("option");
        opt.value = sorted[k];
        opt.textContent = sorted[k];
        fragment.appendChild(opt);
      }

      sel.innerHTML = "";
      sel.appendChild(fragment);

      sel.value = prev;
      if (sel.value !== prev) {
        colFilters[key] = "";
        sel.value = "";
      }
    }
    updateFilterHighlight();
  }

  function updateFilterHighlight() {
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
      icon.textContent = key === sortCol ? (sortDir === "asc" ? " \u25B2" : " \u25BC") : "";
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

  // ─── Фильтрация + сортировка ───
  function applyFilters() {
    var globalFilter = (filterInput ? filterInput.value : "").trim().toLowerCase();
    var rows = cachedRows;

    if (globalFilter) {
      rows = rows.filter(function (row) {
        return getSearchString(row).indexOf(globalFilter) !== -1;
      });
    }

    COLUMNS.forEach(function (col) {
      var f = colFilters[col.key] || "";
      if (!f) return;
      rows = rows.filter(function (row) {
        return String(row[col.key] == null ? "" : row[col.key]) === f;
      });
    });

    if (sortCol) {
      rows = TableUtils.sortRows(rows, sortCol, sortDir, DATE_KEYS);
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
      var service = row.account_type === "Сервис";
      tr.className = rowClass(row.source) + (inactive ? " uz-inactive" : "") + (service ? " uz-service" : "");

      var tdNum = document.createElement("td");
      tdNum.className = "col-num";
      tdNum.textContent = i + 1;
      tr.appendChild(tdNum);

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

  // ─── Throttled scroll для ленивой подгрузки ───
  if (tableContainer) {
    var scrollTimeout = null;
    tableContainer.addEventListener("scroll", function () {
      if (scrollTimeout) return;
      scrollTimeout = setTimeout(function () {
        scrollTimeout = null;
        if (renderedCount >= filteredRows.length) return;
        var el = tableContainer;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 300) {
          renderChunk();
        }
      }, 50);
    });
  }

  // ─── Загрузка данных ───
  async function loadTable() {
    tbody.innerHTML = "<tr><td colspan=\"" + TOTAL_COLS + "\">Загрузка…</td></tr>";
    try {
      var r = await fetch(API + "/api/consolidated");
      var data = await r.json();
      cachedRows = data.rows || [];
      searchCache = new Map();  // Сброс кэша поиска
      updateFilterOptions();
      applyFilters();
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + TOTAL_COLS + "\">Ошибка загрузки: " + esc(e.message) + "</td></tr>";
      tableFooter.textContent = "";
    }
  }

  btnRefresh.onclick = loadTable;
  if (filterInput) {
    filterInput.addEventListener("input", function () { applyFilters(); });
  }

  // ─── Сброс фильтров ───
  var btnResetFilters = document.getElementById("btn-reset-filters");
  if (btnResetFilters) {
    btnResetFilters.onclick = function () {
      colFilters = {};
      sortCol = null;
      sortDir = "asc";
      if (filterInput) filterInput.value = "";
      updateSortIcons();
      updateFilterOptions();
      applyFilters();
    };
  }

  // ─── Экспорт XLSX ───
  var btnExport = document.getElementById("btn-export");
  if (btnExport) {
    btnExport.onclick = function () {
      var data = filteredRows.length ? filteredRows : cachedRows;
      AppUtils.exportToXLSX(COLUMNS, data, "Svodka_AD_MFA_People.xlsx", "Сводная");
    };
  }

  // ─── Инициализация ───
  buildThead();
  loadTable();
})();
