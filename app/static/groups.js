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
    { key: "staff_uuid",   label: "StaffUUID" }
  ];

  var DATE_KEYS = { "password_last_set": true };

  // ─── Состояние ───
  var treeData = [];
  var cachedMembers = [];
  var sortCol = null;
  var sortDir = "asc";
  var selectedGroup = null;
  var selectedDomain = null;

  // ─── DOM ───
  var sidebarTree = document.getElementById("sidebar-tree");
  var groupSearch = document.getElementById("group-search");
  var groupsTitle = document.getElementById("groups-title");
  var groupsCount = document.getElementById("groups-count");
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
    TableUtils.renderMembersTable(tbody, rows, COLUMNS, "Нет участников");
  }

  // ─── Загрузка участников группы ───
  async function loadMembers(group, domain) {
    selectedGroup = group;
    selectedDomain = domain;
    groupsTitle.textContent = group;
    groupsCount.textContent = "загрузка…";
    tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Загрузка…</td></tr>";

    try {
      var data = await AppUtils.fetchJSON(API + "/api/groups/members?group=" + encodeURIComponent(group) + "&domain=" + encodeURIComponent(domain));
      cachedMembers = data.members || [];
      groupsCount.textContent = data.count + " уч. (" + data.city + ")";
      sortCol = null;
      sortDir = "asc";
      TableUtils.updateSortIcons(thead, sortCol, sortDir);
      renderMembers();
      if (btnExport) btnExport.style.display = cachedMembers.length ? "" : "none";
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Ошибка: " + esc(e.message) + "</td></tr>";
      groupsCount.textContent = "";
    }

    highlightSelected(group, domain);
  }

  function highlightSelected(group, domain) {
    var items = sidebarTree.querySelectorAll(".tree-group");
    for (var i = 0; i < items.length; i++) {
      var el = items[i];
      if (el.dataset.group === group && el.dataset.domain === domain) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  }

  // ─── Построение дерева (с event delegation) ───
  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

    var fragment = document.createDocumentFragment();

    treeData.forEach(function (domain) {
      var groups = domain.groups;
      if (filter) {
        groups = groups.filter(function (g) {
          return g.name.toLowerCase().indexOf(filter) !== -1;
        });
      }

      var domainEl = document.createElement("div");
      domainEl.className = "tree-domain";

      var header = document.createElement("div");
      header.className = "tree-domain-header";
      header.innerHTML = "<span class=\"tree-arrow\">&#9660;</span> "
        + esc(domain.city)
        + " <span class=\"tree-badge\">" + groups.length + " гр. / " + domain.total_users + " уч.</span>";
      header.onclick = function () {
        domainEl.classList.toggle("collapsed");
        var arrow = header.querySelector(".tree-arrow");
        arrow.innerHTML = domainEl.classList.contains("collapsed") ? "&#9654;" : "&#9660;";
      };
      domainEl.appendChild(header);

      var list = document.createElement("div");
      list.className = "tree-group-list";

      groups.forEach(function (g) {
        var item = document.createElement("div");
        item.className = "tree-group";
        item.dataset.group = g.name;
        item.dataset.domain = domain.key;
        item.innerHTML = esc(g.name) + " <span class=\"tree-group-count\">(" + g.count + ")</span>";
        if (g.name === selectedGroup && domain.key === selectedDomain) {
          item.classList.add("active");
        }
        list.appendChild(item);
      });

      domainEl.appendChild(list);
      fragment.appendChild(domainEl);
    });

    sidebarTree.appendChild(fragment);
  }

  // Event delegation для клика по группам
  sidebarTree.addEventListener("click", function (e) {
    var groupEl = e.target.closest(".tree-group");
    if (groupEl && groupEl.dataset.group && groupEl.dataset.domain) {
      loadMembers(groupEl.dataset.group, groupEl.dataset.domain);
    }
  });

  // ─── Загрузка дерева ───
  async function loadTree() {
    try {
      var data = await AppUtils.fetchJSON(API + "/api/groups/tree");
      treeData = data.domains || [];
      renderTree();
    } catch (e) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  groupSearch.addEventListener("input", function () {
    renderTree(groupSearch.value);
  });

  // ─── Экспорт XLSX ───
  if (btnExport) {
    btnExport.onclick = function () {
      var safeName = (selectedGroup || "group").replace(/[\\/:*?"<>|]/g, "_");
      AppUtils.exportToXLSX(COLUMNS, cachedMembers, "Group_" + safeName + ".xlsx", safeName);
    };
  }

  // ─── Инициализация ───
  TableUtils.buildSimpleThead(thead, COLUMNS, onSort);
  loadTree().then(function () {
    var params = new URLSearchParams(window.location.search);
    var pGroup = params.get("group");
    var pDomain = params.get("domain");
    if (pGroup && pDomain) {
      loadMembers(pGroup, pDomain);
    }
  });
})();
