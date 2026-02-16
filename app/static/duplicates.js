(function () {
  "use strict";

  var API  = "/api/duplicates";
  var esc  = AppUtils.escapeHtml;

  /* ── Колонки таблицы ── */
  var COLUMNS = [
    { key: "login",             label: "Логин" },
    { key: "domain",            label: "Домен AD" },
    { key: "display_name",      label: "ФИО" },
    { key: "email",             label: "Email" },
    { key: "phone",             label: "Телефон" },
    { key: "mobile",            label: "Мобильный" },
    { key: "enabled",           label: "Активна" },
    { key: "password_last_set", label: "Смена пароля" },
    { key: "account_expires",   label: "Срок УЗ" },
    { key: "staff_uuid",        label: "StaffUUID" },
    { key: "title",             label: "Должность" },
    { key: "department",        label: "Отдел" },
    { key: "company",           label: "Компания" },
  ];

  var DATE_KEYS = { "password_last_set": true, "account_expires": true };

  var allRows    = [];
  var sortCol    = "login";
  var sortDir    = "asc";
  var thead      = document.getElementById("dup-thead");
  var tbody      = document.getElementById("dup-tbody");
  var statsEl    = document.getElementById("dup-stats");

  /* ── Инициализация заголовков ── */
  TableUtils.buildSimpleThead(thead, COLUMNS, function (col) {
    if (sortCol === col) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortCol = col;
      sortDir = "asc";
    }
    TableUtils.updateSortIcons(thead, sortCol, sortDir);
    renderTable();
  });

  /* ── Загрузка данных ── */
  function load() {
    tbody.innerHTML = '<tr><td colspan="' + COLUMNS.length + '" class="muted-text">Загрузка…</td></tr>';
    fetch(API)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        allRows = data.rows || [];
        statsEl.textContent = "Уникальных логинов: " + data.unique_logins + " | Записей: " + data.total_records;
        renderTable();
      })
      .catch(function (e) {
        tbody.innerHTML = '<tr><td colspan="' + COLUMNS.length + '" class="muted-text">Ошибка загрузки: ' + esc(e.message) + '</td></tr>';
      });
  }

  /* ── Рендер таблицы ── */
  function renderTable() {
    var sorted = TableUtils.sortRows(allRows.slice(), sortCol, sortDir, DATE_KEYS);
    TableUtils.updateSortIcons(thead, sortCol, sortDir);

    if (!sorted.length) {
      tbody.innerHTML = '<tr><td colspan="' + COLUMNS.length + '" class="muted-text">Дублей логинов между доменами AD не найдено</td></tr>';
      return;
    }

    var frag = document.createDocumentFragment();

    for (var i = 0; i < sorted.length; i++) {
      var row = sorted[i];
      var tr = document.createElement("tr");

      // Подсветка неактивных УЗ
      if ((row.enabled || "").toLowerCase() === "нет") {
        tr.classList.add("row-inactive");
      }

      for (var c = 0; c < COLUMNS.length; c++) {
        var td = document.createElement("td");
        var val = row[COLUMNS[c].key] || "";
        td.textContent = val;
        tr.appendChild(td);
      }
      frag.appendChild(tr);
    }
    tbody.innerHTML = "";
    tbody.appendChild(frag);

    // Визуальное разделение групп — через класс row-group-sep
    highlightGroups();
  }

  /* ── Визуальное разделение групп дублей ── */
  function highlightGroups() {
    var rows = tbody.querySelectorAll("tr");
    var prevLogin = "";
    var groupIdx = 0;

    for (var i = 0; i < rows.length; i++) {
      var loginCell = rows[i].querySelector("td");
      var login = loginCell ? loginCell.textContent.toLowerCase() : "";
      if (login !== prevLogin) {
        prevLogin = login;
        groupIdx++;
        if (i > 0) {
          rows[i].classList.add("dup-group-sep");
        }
      }
      if (groupIdx % 2 === 0) {
        rows[i].classList.add("dup-group-alt");
      }
    }
  }

  /* ── Экспорт XLSX ── */
  document.getElementById("btn-export").addEventListener("click", function () {
    if (!allRows.length) return;
    AppUtils.exportToXLSX(COLUMNS, allRows, "Дубли_логинов_AD.xlsx", "Дубли");
  });

  /* ── Старт ── */
  load();
})();
