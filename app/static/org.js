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

  // ─── DOM ───
  var sidebarTree = document.getElementById("sidebar-tree");
  var orgSearch = document.getElementById("org-search");
  var orgTitle = document.getElementById("org-title");
  var orgCount = document.getElementById("org-count");
  var thead = document.getElementById("members-thead");
  var tbody = document.getElementById("members-tbody");
  var btnExport = document.getElementById("btn-export");

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
    var rows = TableUtils.sortRows(cachedMembers, sortCol, sortDir, DATE_KEYS);
    TableUtils.renderMembersTable(tbody, rows, COLUMNS, "Нет пользователей");
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
      orgCount.textContent = data.count + " чел.";
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
    var items = sidebarTree.querySelectorAll(".tree-org-item");
    for (var i = 0; i < items.length; i++) {
      var el = items[i];
      var match = el.dataset.company === (selectedCompany || "")
        && el.dataset.department === (selectedDepartment || "");
      if (match) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  }

  // ─── Построение дерева Company → Department (без домена) ───
  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

    var fragment = document.createDocumentFragment();

    var companies = treeData;
    if (filter) {
      companies = companies.filter(function (c) {
        if (c.name.toLowerCase().indexOf(filter) !== -1) return true;
        return c.departments.some(function (d) {
          return d.name.toLowerCase().indexOf(filter) !== -1;
        });
      });
    }

    if (!companies.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет результатов</p>";
      return;
    }

    companies.forEach(function (comp) {
      var compEl = document.createElement("div");
      compEl.className = "tree-org-company";

      var compRow = document.createElement("div");
      compRow.className = "tree-ou-row";

      var arrow = document.createElement("span");
      arrow.className = "tree-arrow";
      arrow.innerHTML = "&#9654;";
      compRow.appendChild(arrow);

      var compLabel = document.createElement("span");
      compLabel.className = "tree-org-item";
      compLabel.dataset.company = comp.name;
      compLabel.dataset.department = "";
      compLabel.innerHTML = esc(comp.name)
        + " <span class=\"tree-group-count\">(" + comp.count + ")</span>";
      compRow.appendChild(compLabel);
      compEl.appendChild(compRow);

      var deptWrap = document.createElement("div");
      deptWrap.className = "tree-ou-children";
      deptWrap.style.display = "none";

      var depts = comp.departments;
      if (filter) {
        depts = depts.filter(function (d) {
          return d.name.toLowerCase().indexOf(filter) !== -1
            || comp.name.toLowerCase().indexOf(filter) !== -1;
        });
      }

      depts.forEach(function (dept) {
        var deptRow = document.createElement("div");
        deptRow.className = "tree-ou-row";

        var spacer = document.createElement("span");
        spacer.className = "tree-arrow-spacer";
        deptRow.appendChild(spacer);

        var deptLabel = document.createElement("span");
        deptLabel.className = "tree-org-item";
        deptLabel.dataset.company = comp.name;
        deptLabel.dataset.department = dept.name;
        deptLabel.innerHTML = esc(dept.name)
          + " <span class=\"tree-group-count\">(" + dept.count + ")</span>";
        deptRow.appendChild(deptLabel);
        deptWrap.appendChild(deptRow);
      });

      if (filter) {
        deptWrap.style.display = "";
        arrow.innerHTML = "&#9660;";
      }

      compEl.appendChild(deptWrap);
      fragment.appendChild(compEl);
    });

    sidebarTree.appendChild(fragment);
  }

  // Event delegation для дерева
  sidebarTree.addEventListener("click", function (e) {
    var arrow = e.target.closest(".tree-arrow");
    if (arrow) {
      var row = arrow.closest(".tree-ou-row");
      if (row) {
        var nodeEl = row.parentElement;
        var childContainer = nodeEl.querySelector(".tree-ou-children");
        if (childContainer) {
          var isHidden = childContainer.style.display === "none";
          childContainer.style.display = isHidden ? "" : "none";
          arrow.innerHTML = isHidden ? "&#9660;" : "&#9654;";
        }
      }
      return;
    }

    var item = e.target.closest(".tree-org-item");
    if (item) {
      loadMembers(item.dataset.company || "", item.dataset.department || "");
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

  // ─── Экспорт XLSX ───
  if (btnExport) {
    btnExport.onclick = function () {
      var name = (selectedDepartment || selectedCompany || "org").replace(/[\\/:*?"<>|]/g, "_");
      AppUtils.exportToXLSX(COLUMNS, cachedMembers, "Org_" + name + ".xlsx", name);
    };
  }

  // ─── Инициализация ───
  TableUtils.buildSimpleThead(thead, COLUMNS, onSort);
  loadTree();
})();
