(function () {
  var API = AppUtils.API;
  var esc = AppUtils.escapeHtml;

  var COLUMNS = [
    { key: "login",        label: "Логин" },
    { key: "display_name", label: "ФИО" },
    { key: "email",        label: "Email" },
    { key: "enabled",      label: "УЗ активна" },
    { key: "password_last_set", label: "Смена пароля" },
    { key: "title",        label: "Должность" },
    { key: "department",   label: "Отдел" },
    { key: "company",      label: "Компания" },
    { key: "location",     label: "Город" },
    { key: "domain",       label: "Домен" },
    { key: "staff_uuid",   label: "StaffUUID" }
  ];

  var DATE_KEYS = { "password_last_set": true };

  // ─── Состояние ───
  var treeData = [];
  var cachedMembers = [];
  var sortCol = null;
  var sortDir = "asc";
  var selectedCompany = null;
  var selectedDepartment = null;
  var hideDisabled = false;

  // ─── DOM ───
  var sidebarTree = document.getElementById("sidebar-tree");
  var orgSearch = document.getElementById("org-search");
  var orgTitle = document.getElementById("org-title");
  var orgCount = document.getElementById("org-count");
  var thead = document.getElementById("members-thead");
  var tbody = document.getElementById("members-tbody");
  var btnExport = document.getElementById("btn-export");
  var hideDisabledCb = document.getElementById("hide-disabled");

  // ─── Сортировка ───
  function onSort(key) {
    if (sortCol === key) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortCol = key;
      sortDir = "asc";
    }
    TableUtils.updateSortIcons(thead, sortCol, sortDir);
    renderMembers();
  }

  function renderMembers() {
    var data = cachedMembers;
    if (hideDisabled) {
      data = data.filter(function (m) {
        return (m.enabled || "").toLowerCase() !== "нет";
      });
    }
    var rows = TableUtils.sortRows(data, sortCol, sortDir, DATE_KEYS);
    TableUtils.renderMembersTable(tbody, rows, COLUMNS, "Нет пользователей");
    updateCount(data.length);
  }

  function updateCount(visibleCount) {
    var total = cachedMembers.length;
    var text = visibleCount + " чел.";
    if (hideDisabled && visibleCount < total) {
      text += " (скрыто " + (total - visibleCount) + " откл.)";
    }
    orgCount.textContent = text;
  }

  // ─── Загрузка участников ───
  async function loadMembers(company, department) {
    selectedCompany = company;
    selectedDepartment = department;

    var titleParts = [];
    if (company) titleParts.push(company);
    if (department) titleParts.push(department);
    orgTitle.textContent = titleParts.join(" → ") || "Все";
    orgCount.textContent = "загрузка…";
    tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Загрузка…</td></tr>";

    try {
      var url = API + "/api/org/members?";
      if (company) url += "company=" + encodeURIComponent(company) + "&";
      if (department) url += "department=" + encodeURIComponent(department);
      var r = await fetch(url);
      var data = await r.json();
      cachedMembers = data.members || [];
      sortCol = null;
      sortDir = "asc";
      TableUtils.updateSortIcons(thead, sortCol, sortDir);
      renderMembers();
      if (btnExport) btnExport.style.display = cachedMembers.length ? "" : "none";
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Ошибка: " + esc(e.message) + "</td></tr>";
      orgCount.textContent = "";
    }

    highlightSelected();
  }

  function highlightSelected() {
    var headers = sidebarTree.querySelectorAll(".tree-org-header");
    for (var i = 0; i < headers.length; i++) {
      var h = headers[i];
      if (h.dataset.company === (selectedCompany || "") && !selectedDepartment) {
        h.classList.add("active");
      } else {
        h.classList.remove("active");
      }
    }
    var depts = sidebarTree.querySelectorAll(".tree-org-dept");
    for (var j = 0; j < depts.length; j++) {
      var d = depts[j];
      if (d.dataset.company === (selectedCompany || "") && d.dataset.department === (selectedDepartment || "")) {
        d.classList.add("active");
      } else {
        d.classList.remove("active");
      }
    }
  }

  // ─── Построение дерева Company → Department ───
  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

    var companies = treeData;

    // Текстовый фильтр
    if (filter) {
      companies = companies.filter(function (c) {
        if (c.name.toLowerCase().indexOf(filter) !== -1) return true;
        return c.departments.some(function (d) {
          return d.name.toLowerCase().indexOf(filter) !== -1;
        });
      });
    }

    // Фильтр «скрыть заблокированные»: убираем компании без активных УЗ
    if (hideDisabled) {
      companies = companies.filter(function (c) {
        return (c.enabled_count || 0) > 0;
      });
    }

    if (!companies.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет результатов</p>";
      return;
    }

    var fragment = document.createDocumentFragment();

    companies.forEach(function (comp) {
      var domainEl = document.createElement("div");
      domainEl.className = "tree-domain";

      // Заголовок компании
      var header = document.createElement("div");
      header.className = "tree-domain-header tree-org-header";
      header.dataset.company = comp.name;

      var arrow = document.createElement("span");
      arrow.className = "tree-arrow";
      arrow.innerHTML = "&#9660;";
      header.appendChild(arrow);

      var nameSpan = document.createElement("span");
      nameSpan.className = "tree-org-name";
      nameSpan.textContent = comp.name;
      header.appendChild(nameSpan);

      var dispCount = hideDisabled ? (comp.enabled_count || 0) : comp.count;
      var badge = document.createElement("span");
      badge.className = "tree-badge";
      badge.textContent = comp.departments.length + " отд. / " + dispCount + " чел.";
      header.appendChild(badge);

      domainEl.appendChild(header);

      // Список отделов
      var deptList = document.createElement("div");
      deptList.className = "tree-group-list";

      var depts = comp.departments;

      if (filter) {
        depts = depts.filter(function (d) {
          return d.name.toLowerCase().indexOf(filter) !== -1
            || comp.name.toLowerCase().indexOf(filter) !== -1;
        });
      }

      // Скрываем отделы без активных УЗ
      if (hideDisabled) {
        depts = depts.filter(function (d) {
          return (d.enabled_count || 0) > 0;
        });
      }

      depts.forEach(function (dept) {
        var item = document.createElement("div");
        item.className = "tree-group tree-org-dept";
        item.dataset.company = comp.name;
        item.dataset.department = dept.name;
        var deptCount = hideDisabled ? (dept.enabled_count || 0) : dept.count;
        item.innerHTML = esc(dept.name) + " <span class=\"tree-group-count\">(" + deptCount + ")</span>";
        deptList.appendChild(item);
      });

      domainEl.appendChild(deptList);
      fragment.appendChild(domainEl);
    });

    sidebarTree.appendChild(fragment);
    highlightSelected();
  }

  // ─── Event delegation для дерева ───
  sidebarTree.addEventListener("click", function (e) {
    // Клик по отделу
    var dept = e.target.closest(".tree-org-dept");
    if (dept) {
      loadMembers(dept.dataset.company || "", dept.dataset.department || "");
      return;
    }

    // Клик по заголовку компании
    var header = e.target.closest(".tree-org-header");
    if (!header) return;

    var arrowEl = e.target.closest(".tree-arrow");
    if (arrowEl) {
      // Стрелка → toggle collapse
      var domainEl = header.closest(".tree-domain");
      domainEl.classList.toggle("collapsed");
      arrowEl.innerHTML = domainEl.classList.contains("collapsed") ? "&#9654;" : "&#9660;";
    } else {
      // Имя компании → загрузить всех сотрудников компании
      loadMembers(header.dataset.company || "", "");
    }
  });

  // ─── Загрузка дерева ───
  async function loadTree() {
    try {
      var r = await fetch(API + "/api/org/tree");
      var data = await r.json();
      treeData = data.companies || [];
      renderTree();
    } catch (e) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  orgSearch.addEventListener("input", function () {
    renderTree(orgSearch.value);
  });

  // ─── Галочка «Скрыть заблокированные» ───
  function onHideDisabledToggle() {
    hideDisabled = hideDisabledCb.checked;
    renderTree(orgSearch.value);
    renderMembers();
  }

  if (hideDisabledCb) {
    hideDisabledCb.addEventListener("change", onHideDisabledToggle);
    hideDisabledCb.addEventListener("click", onHideDisabledToggle);
  }

  // ─── Экспорт XLSX ───
  if (btnExport) {
    btnExport.onclick = function () {
      var name = (selectedDepartment || selectedCompany || "org").replace(/[\\/:*?"<>|]/g, "_");
      var data = cachedMembers;
      if (hideDisabled) {
        data = data.filter(function (m) {
          return (m.enabled || "").toLowerCase() !== "нет";
        });
      }
      AppUtils.exportToXLSX(COLUMNS, data, "Org_" + name + ".xlsx", name);
    };
  }

  // ─── Инициализация ───
  TableUtils.buildSimpleThead(thead, COLUMNS, onSort);
  loadTree();
})();
