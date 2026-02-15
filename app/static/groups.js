(function () {
  var API = "";

  // ─── Колонки таблицы участников ───
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

  // Колонки с датами
  var DATE_KEYS = { "password_last_set": true };

  function dateSortKey(val) {
    if (!val) return "";
    var m = val.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (m) return m[3] + m[2] + m[1];
    return val;
  }

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

  // ─── Утилиты ───
  function escapeHtml(s) {
    if (s == null || s === undefined) return "";
    var t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  }

  // ─── Построение заголовка таблицы ───
  function buildThead() {
    thead.innerHTML = "";
    var tr = document.createElement("tr");
    COLUMNS.forEach(function (col) {
      var th = document.createElement("th");
      th.className = "sortable";
      th.dataset.key = col.key;
      th.innerHTML = escapeHtml(col.label) + " <span class=\"sort-icon\"></span>";
      th.onclick = function () { onSort(col.key); };
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    updateSortIcons();
  }

  function updateSortIcons() {
    var ths = thead.querySelectorAll("th");
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
    renderMembers();
  }

  // ─── Рендер таблицы участников ───
  function renderMembers() {
    var rows = cachedMembers.slice();

    if (sortCol) {
      var dir = sortDir === "asc" ? 1 : -1;
      var isDate = !!DATE_KEYS[sortCol];
      rows.sort(function (a, b) {
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
        if (va > vb) return 1 * dir;
        return 0;
      });
    }

    if (rows.length === 0) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Нет участников</td></tr>";
      return;
    }

    tbody.innerHTML = rows.map(function (row) {
      var inactive = row.enabled === "Нет";
      var cls = inactive ? " class=\"uz-inactive\"" : "";
      var cells = COLUMNS.map(function (col) {
        return "<td>" + escapeHtml(row[col.key]) + "</td>";
      }).join("");
      return "<tr" + cls + ">" + cells + "</tr>";
    }).join("");
  }

  // ─── Загрузка участников группы ───
  async function loadMembers(group, domain) {
    selectedGroup = group;
    selectedDomain = domain;
    groupsTitle.textContent = group;
    groupsCount.textContent = "загрузка…";
    tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Загрузка…</td></tr>";

    try {
      var r = await fetch(API + "/api/groups/members?group=" + encodeURIComponent(group) + "&domain=" + encodeURIComponent(domain));
      var data = await r.json();
      cachedMembers = data.members || [];
      groupsCount.textContent = data.count + " уч. (" + data.city + ")";
      sortCol = null;
      sortDir = "asc";
      updateSortIcons();
      renderMembers();
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Ошибка: " + escapeHtml(e.message) + "</td></tr>";
      groupsCount.textContent = "";
    }

    // Подсветить выбранную группу в дереве
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

  // ─── Построение дерева ───
  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

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
        + escapeHtml(domain.city)
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
        item.innerHTML = escapeHtml(g.name) + " <span class=\"tree-group-count\">(" + g.count + ")</span>";
        item.onclick = function () {
          loadMembers(g.name, domain.key);
        };
        // Восстановить подсветку
        if (g.name === selectedGroup && domain.key === selectedDomain) {
          item.classList.add("active");
        }
        list.appendChild(item);
      });

      domainEl.appendChild(list);
      sidebarTree.appendChild(domainEl);
    });
  }

  // ─── Загрузка дерева ───
  async function loadTree() {
    try {
      var r = await fetch(API + "/api/groups/tree");
      var data = await r.json();
      treeData = data.domains || [];
      renderTree();
    } catch (e) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Ошибка: " + escapeHtml(e.message) + "</p>";
    }
  }

  // ─── Поиск по группам ───
  groupSearch.addEventListener("input", function () {
    renderTree(groupSearch.value);
  });

  // ─── Инициализация ───
  buildThead();
  loadTree();
})();
