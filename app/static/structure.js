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
  var selectedPath = null;
  var selectedDomain = null;

  // ─── DOM ───
  var sidebarTree = document.getElementById("sidebar-tree");
  var ouSearch = document.getElementById("ou-search");
  var ouTitle = document.getElementById("ou-title");
  var ouBreadcrumb = document.getElementById("ou-breadcrumb");
  var ouCount = document.getElementById("ou-count");
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
    TableUtils.renderMembersTable(tbody, rows, COLUMNS, "Нет пользователей в этом OU");
  }

  // ─── Хлебные крошки (с event delegation) ───
  function renderBreadcrumb(path, domain) {
    if (!path) { ouBreadcrumb.innerHTML = ""; return; }
    var parts = path.split("/");
    ouBreadcrumb.innerHTML = parts.map(function (p, i) {
      var sub = parts.slice(0, i + 1).join("/");
      return "<span class=\"ou-crumb\" data-path=\"" + esc(sub) + "\" data-domain=\"" + esc(domain) + "\">"
        + esc(p) + "</span>";
    }).join(" <span class=\"ou-crumb-sep\">›</span> ");
  }

  // Event delegation для хлебных крошек
  ouBreadcrumb.addEventListener("click", function (e) {
    var crumb = e.target.closest(".ou-crumb");
    if (crumb) {
      loadMembers(crumb.dataset.path, crumb.dataset.domain);
    }
  });

  // ─── Загрузка участников OU ───
  async function loadMembers(path, domain) {
    selectedPath = path;
    selectedDomain = domain;
    ouTitle.textContent = path.split("/").pop();
    ouCount.textContent = "загрузка…";
    renderBreadcrumb(path, domain);
    tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Загрузка…</td></tr>";

    try {
      var data = await AppUtils.fetchJSON(API + "/api/structure/members?path=" + encodeURIComponent(path) + "&domain=" + encodeURIComponent(domain));
      cachedMembers = data.members || [];
      ouCount.textContent = data.count + " уч. (" + data.city + ")";
      sortCol = null;
      sortDir = "asc";
      TableUtils.updateSortIcons(thead, sortCol, sortDir);
      renderMembers();
      if (btnExport) btnExport.style.display = cachedMembers.length ? "" : "none";
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Ошибка: " + esc(e.message) + "</td></tr>";
      ouCount.textContent = "";
    }

    highlightSelected();
  }

  function highlightSelected() {
    var items = sidebarTree.querySelectorAll(".tree-ou-item");
    for (var i = 0; i < items.length; i++) {
      var el = items[i];
      if (el.dataset.path === selectedPath && el.dataset.domain === selectedDomain) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  }

  // ─── Построение дерева OU (рекурсивно) ───
  function buildTreeNode(children, parentPath, domainKey, filter) {
    var container = document.createElement("div");
    container.className = "tree-ou-children";

    children.forEach(function (node) {
      var nameMatch = !filter || node.name.toLowerCase().indexOf(filter) !== -1;
      var childrenMatch = hasFilterMatch(node.children, filter);
      if (filter && !nameMatch && !childrenMatch) return;

      var nodePath = parentPath ? parentPath + "/" + node.name : node.name;
      var nodeEl = document.createElement("div");
      nodeEl.className = "tree-ou-node";
      var hasChildren = node.children && node.children.length > 0;

      var row = document.createElement("div");
      row.className = "tree-ou-row";

      if (hasChildren) {
        var arrow = document.createElement("span");
        arrow.className = "tree-arrow";
        arrow.innerHTML = "&#9654;";
        row.appendChild(arrow);
      } else {
        var spacer = document.createElement("span");
        spacer.className = "tree-arrow-spacer";
        row.appendChild(spacer);
      }

      var label = document.createElement("span");
      label.className = "tree-ou-item";
      label.dataset.path = nodePath;
      label.dataset.domain = domainKey;
      label.innerHTML = esc(node.name)
        + " <span class=\"tree-group-count\">(" + node.count + "/" + node.total + ")</span>";

      if (nodePath === selectedPath && domainKey === selectedDomain) {
        label.classList.add("active");
      }

      row.appendChild(label);
      nodeEl.appendChild(row);

      if (hasChildren) {
        var childContainer = buildTreeNode(node.children, nodePath, domainKey, filter);
        childContainer.style.display = "none";

        if (filter && childrenMatch) {
          childContainer.style.display = "";
          if (row.querySelector(".tree-arrow")) {
            row.querySelector(".tree-arrow").innerHTML = "&#9660;";
          }
        }

        nodeEl.appendChild(childContainer);
      }

      container.appendChild(nodeEl);
    });

    return container;
  }

  function hasFilterMatch(children, filter) {
    if (!filter || !children) return false;
    for (var i = 0; i < children.length; i++) {
      if (children[i].name.toLowerCase().indexOf(filter) !== -1) return true;
      if (hasFilterMatch(children[i].children, filter)) return true;
    }
    return false;
  }

  // Event delegation для дерева OU
  sidebarTree.addEventListener("click", function (e) {
    // Клик по стрелке — раскрытие/свёртывание
    var arrow = e.target.closest(".tree-arrow");
    if (arrow) {
      e.stopPropagation();
      var row = arrow.closest(".tree-ou-row");
      if (!row) return;
      var nodeEl = row.parentElement;
      var childContainer = nodeEl.querySelector(".tree-ou-children");
      if (childContainer) {
        var isHidden = childContainer.style.display === "none";
        childContainer.style.display = isHidden ? "" : "none";
        arrow.innerHTML = isHidden ? "&#9660;" : "&#9654;";
      }
      return;
    }
    // Клик по OU-элементу
    var ouItem = e.target.closest(".tree-ou-item");
    if (ouItem && ouItem.dataset.path && ouItem.dataset.domain) {
      loadMembers(ouItem.dataset.path, ouItem.dataset.domain);
    }
  });

  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

    var fragment = document.createDocumentFragment();

    treeData.forEach(function (domain) {
      if (!domain.tree || !domain.tree.length) return;

      var domainEl = document.createElement("div");
      domainEl.className = "tree-domain";

      var header = document.createElement("div");
      header.className = "tree-domain-header";
      header.innerHTML = "<span class=\"tree-arrow\">&#9660;</span> "
        + esc(domain.city)
        + " <span class=\"tree-badge\">" + domain.total_users + " уч.</span>";

      var content = buildTreeNode(domain.tree, "", domain.key, filter);

      header.onclick = function () {
        domainEl.classList.toggle("collapsed");
        var a = header.querySelector(".tree-arrow");
        a.innerHTML = domainEl.classList.contains("collapsed") ? "&#9654;" : "&#9660;";
        content.style.display = domainEl.classList.contains("collapsed") ? "none" : "";
      };

      domainEl.appendChild(header);
      domainEl.appendChild(content);
      fragment.appendChild(domainEl);
    });

    sidebarTree.appendChild(fragment);
  }

  async function loadTree() {
    try {
      var data = await AppUtils.fetchJSON(API + "/api/structure/tree");
      treeData = data.domains || [];
      renderTree();
    } catch (e) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  ouSearch.addEventListener("input", function () {
    renderTree(ouSearch.value);
  });

  // ─── Экспорт XLSX ───
  if (btnExport) {
    btnExport.onclick = function () {
      var ouName = (selectedPath || "ou").split("/").pop().replace(/[\\/:*?"<>|]/g, "_");
      AppUtils.exportToXLSX(COLUMNS, cachedMembers, "OU_" + ouName + ".xlsx", ouName);
    };
  }

  // ─── Инициализация ───
  TableUtils.buildSimpleThead(thead, COLUMNS, onSort);
  loadTree().then(function () {
    var params = new URLSearchParams(window.location.search);
    var pPath = params.get("path");
    var pDomain = params.get("domain");
    if (pPath && pDomain) {
      loadMembers(pPath, pDomain);
    }
  });
})();
