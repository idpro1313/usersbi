(function () {
  var API = "";

  // ─── Определение колонок таблицы ───
  var COLUMNS = [
    { key: "source",             label: "Источник" },
    { key: "login",              label: "Логин" },
    { key: "domain",             label: "Домен" },
    { key: "uz_active",          label: "УЗ" },
    { key: "password_last_set",  label: "Пароль" },
    { key: "account_expires",    label: "Срок УЗ" },
    { key: "staff_uuid",         label: "UUID" },
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
    { key: "phone_mfa",          label: "Тел. (MFA)" },
    { key: "phone_people",       label: "Тел. (Кадры)" },
    { key: "discrepancies",      label: "Расхождения" }
  ];

  // ─── Состояние ───
  var cachedRows = [];
  var sortCol = null;
  var sortDir = "asc";        // "asc" | "desc"
  var colFilters = {};         // { key: "строка" }

  // ─── DOM ───
  var thead = document.getElementById("thead");
  var tbody = document.getElementById("tbody");
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

  function rowClass(source) {
    if (source === "AD") return "source-ad";
    if (source === "MFA") return "source-mfa";
    if (source === "Кадры") return "source-people";
    return "";
  }

  // ─── Генерация заголовков (два ряда: метки + фильтры) ───
  function buildThead() {
    thead.innerHTML = "";

    // Ряд 1: метки + сортировка
    var trLabels = document.createElement("tr");
    trLabels.className = "thead-labels";
    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      th.className = "sortable";
      th.dataset.key = col.key;
      th.innerHTML = escapeHtml(col.label) + " <span class=\"sort-icon\"></span>";
      th.onclick = function () { onSort(col.key); };
      trLabels.appendChild(th);
    });
    thead.appendChild(trLabels);

    // Ряд 2: фильтры по столбцам
    var trFilters = document.createElement("tr");
    trFilters.className = "thead-filters";
    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      var inp = document.createElement("input");
      inp.type = "text";
      inp.className = "col-filter";
      inp.placeholder = "…";
      inp.dataset.key = col.key;
      inp.value = colFilters[col.key] || "";
      inp.addEventListener("input", function () {
        colFilters[col.key] = inp.value;
        renderTable();
      });
      th.appendChild(inp);
      trFilters.appendChild(th);
    });
    thead.appendChild(trFilters);

    updateSortIcons();
  }

  function updateSortIcons() {
    var ths = thead.querySelectorAll(".thead-labels th");
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
    renderTable();
  }

  // ─── Фильтрация + сортировка + рендер ───
  function renderTable() {
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
      var f = (colFilters[col.key] || "").trim().toLowerCase();
      if (!f) return;
      rows = rows.filter(function (row) {
        var val = (row[col.key] == null ? "" : String(row[col.key])).toLowerCase();
        return val.indexOf(f) !== -1;
      });
    });

    // 3) Сортировка
    if (sortCol) {
      var dir = sortDir === "asc" ? 1 : -1;
      rows = rows.slice().sort(function (a, b) {
        var va = (a[sortCol] == null ? "" : String(a[sortCol])).toLowerCase();
        var vb = (b[sortCol] == null ? "" : String(b[sortCol])).toLowerCase();
        if (va < vb) return -1 * dir;
        if (va > vb) return  1 * dir;
        return 0;
      });
    }

    // 4) Рендер строк
    tbody.innerHTML = rows.map(function (row) {
      var cells = COLUMNS.map(function (col) {
        var cls = col.key === "discrepancies" ? " class=\"discrepancy\"" : "";
        return "<td" + cls + ">" + escapeHtml(row[col.key]) + "</td>";
      }).join("");
      return "<tr class=\"" + rowClass(row.source) + "\">" + cells + "</tr>";
    }).join("");

    // 5) Счётчик
    var total = cachedRows.length;
    var shown = rows.length;
    var suffix = shown < total ? " (показано: " + shown + ")" : "";
    tableFooter.textContent = "Всего записей: " + total + suffix;
  }

  // ─── Загрузка данных ───
  async function loadTable() {
    try {
      var r = await fetch(API + "/api/consolidated");
      var data = await r.json();
      cachedRows = data.rows || [];
      renderTable();
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\">Ошибка загрузки: " + escapeHtml(e.message) + "</td></tr>";
      tableFooter.textContent = "";
    }
  }

  btnRefresh.onclick = loadTable;
  if (filterInput) {
    filterInput.addEventListener("input", function () { renderTable(); });
  }

  // ─── Загрузка файлов ───
  function setStatus(el, ok, msg) {
    el.textContent = msg;
    el.className = "upload-status " + (ok ? "ok" : "err");
  }

  async function upload(fileInput, endpoint, statusEl) {
    var file = fileInput.files[0];
    if (!file) return;
    var form = new FormData();
    form.append("file", file);
    try {
      var r = await fetch(API + endpoint, { method: "POST", body: form });
      var data = await r.json();
      if (!r.ok) {
        setStatus(statusEl, false, data.detail || "Ошибка загрузки");
        return;
      }
      setStatus(statusEl, true, "Загружено: " + data.rows + " записей (" + data.filename + ")");
      loadStats();
      loadTable();
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  // AD домены
  var adDomains = ["izhevsk", "kostroma", "moscow"];
  var adFiles = {}, adBtns = {}, adStatuses = {};
  adDomains.forEach(function (key) {
    adFiles[key] = document.getElementById("file-ad-" + key);
    adBtns[key] = document.getElementById("btn-ad-" + key);
    adStatuses[key] = document.getElementById("status-ad-" + key);
    if (adBtns[key]) adBtns[key].onclick = function () { adFiles[key].click(); };
    if (adFiles[key]) adFiles[key].onchange = function () { upload(adFiles[key], "/api/upload/ad/" + key, adStatuses[key]); };
  });

  var fileMfa = document.getElementById("file-mfa");
  var filePeople = document.getElementById("file-people");
  var btnMfa = document.getElementById("btn-mfa");
  var btnPeople = document.getElementById("btn-people");
  var statusMfa = document.getElementById("status-mfa");
  var statusPeople = document.getElementById("status-people");
  btnMfa.onclick = function () { fileMfa.click(); };
  btnPeople.onclick = function () { filePeople.click(); };
  fileMfa.onchange = function () { upload(fileMfa, "/api/upload/mfa", statusMfa); };
  filePeople.onchange = function () { upload(filePeople, "/api/upload/people", statusPeople); };

  // ─── Статистика ───
  var statsEl = document.getElementById("stats");
  async function loadStats() {
    try {
      var r = await fetch(API + "/api/stats");
      var s = await r.json();
      var parts = [];
      if (s.ad_domains) {
        var adParts = [];
        for (var key in s.ad_domains) {
          var d = s.ad_domains[key];
          adParts.push(d.city + ": " + d.rows);
        }
        parts.push("AD: " + s.ad_total + " (" + adParts.join(", ") + ")");
      }
      parts.push("MFA: " + s.mfa_rows);
      parts.push("Кадры: " + s.people_rows);
      statsEl.innerHTML = parts.join(" \u00B7 ");
    } catch (_) {
      statsEl.textContent = "Не удалось загрузить статистику";
    }
  }

  // ─── Очистка БД ───
  async function clearData(endpoint, label, statusEl) {
    if (!confirm("Очистить данные " + label + "?")) return;
    try {
      var r = await fetch(API + endpoint, { method: "DELETE" });
      var data = await r.json();
      if (r.ok) {
        setStatus(statusEl, true, "Удалено: " + data.deleted + " записей");
        loadStats();
        loadTable();
      } else {
        setStatus(statusEl, false, "Ошибка очистки");
      }
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  var adCityNames = { izhevsk: "AD Ижевск", kostroma: "AD Кострома", moscow: "AD Москва" };
  adDomains.forEach(function (key) {
    var btn = document.getElementById("btn-clear-ad-" + key);
    if (btn) btn.onclick = function () { clearData("/api/clear/ad/" + key, adCityNames[key], adStatuses[key]); };
  });

  var btnClearMfa = document.getElementById("btn-clear-mfa");
  var btnClearPeople = document.getElementById("btn-clear-people");
  if (btnClearMfa) btnClearMfa.onclick = function () { clearData("/api/clear/mfa", "MFA", statusMfa); };
  if (btnClearPeople) btnClearPeople.onclick = function () { clearData("/api/clear/people", "Кадры", statusPeople); };

  var btnClearAll = document.getElementById("btn-clear-all");
  if (btnClearAll) {
    btnClearAll.onclick = async function () {
      if (!confirm("Очистить ВСЮ базу данных (AD + MFA + Кадры)?")) return;
      try {
        var r = await fetch(API + "/api/clear/all", { method: "DELETE" });
        var data = await r.json();
        if (r.ok) {
          var d = data.deleted;
          alert("Удалено: AD " + d.ad + ", MFA " + d.mfa + ", Кадры " + d.people);
          loadStats();
          loadTable();
        }
      } catch (e) {
        alert("Ошибка: " + e.message);
      }
    };
  }

  // ─── Экспорт XLSX ───
  var btnExport = document.getElementById("btn-export");
  if (btnExport) {
    btnExport.onclick = function () {
      window.location.href = API + "/api/export/xlsx";
    };
  }

  // ─── Сворачивание панели загрузки ───
  var toggleBtn = document.getElementById("toggle-uploads");
  var uploadsPanel = document.getElementById("uploads-panel");
  if (toggleBtn && uploadsPanel) {
    toggleBtn.onclick = function () {
      uploadsPanel.classList.toggle("collapsed");
      toggleBtn.textContent = uploadsPanel.classList.contains("collapsed")
        ? "Загрузка файлов \u25B6"
        : "Загрузка файлов \u25BC";
    };
  }

  // ─── Инициализация ───
  buildThead();
  loadStats();
  loadTable();
})();
