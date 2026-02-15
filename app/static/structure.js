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

  // ─── Утилиты ───
  function escapeHtml(s) {
    if (s == null || s === undefined) return "";
    var t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  }

  // ─── Заголовок таблицы ───
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

  // ─── Рендер таблицы ───
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
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Нет пользователей в этом OU</td></tr>";
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

  // ─── Хлебные крошки ───
  function renderBreadcrumb(path, domain) {
    if (!path) { ouBreadcrumb.innerHTML = ""; return; }
    var parts = path.split("/");
    var html = parts.map(function (p, i) {
      var sub = parts.slice(0, i + 1).join("/");
      return "<span class=\"ou-crumb\" data-path=\"" + escapeHtml(sub) + "\" data-domain=\"" + escapeHtml(domain) + "\">"
        + escapeHtml(p) + "</span>";
    }).join(" <span class=\"ou-crumb-sep\">›</span> ");
    ouBreadcrumb.innerHTML = html;

    // Клики по крошкам
    var crumbs = ouBreadcrumb.querySelectorAll(".ou-crumb");
    for (var i = 0; i < crumbs.length; i++) {
      crumbs[i].onclick = function () {
        loadMembers(this.dataset.path, this.dataset.domain);
      };
    }
  }

  // ─── Загрузка участников OU ───
  async function loadMembers(path, domain) {
    selectedPath = path;
    selectedDomain = domain;
    var ouName = path.split("/").pop();
    ouTitle.textContent = ouName;
    ouCount.textContent = "загрузка…";
    renderBreadcrumb(path, domain);
    tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Загрузка…</td></tr>";

    try {
      var r = await fetch(API + "/api/structure/members?path=" + encodeURIComponent(path) + "&domain=" + encodeURIComponent(domain));
      var data = await r.json();
      cachedMembers = data.members || [];
      ouCount.textContent = data.count + " уч. (" + data.city + ")";
      sortCol = null;
      sortDir = "asc";
      updateSortIcons();
      renderMembers();
      if (btnExport) btnExport.style.display = cachedMembers.length ? "" : "none";
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"" + COLUMNS.length + "\" class=\"muted-text\">Ошибка: " + escapeHtml(e.message) + "</td></tr>";
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
      // Фильтрация: показать узел, если он или его потомки содержат совпадение
      var nameMatch = !filter || node.name.toLowerCase().indexOf(filter) !== -1;
      var childrenMatch = hasFilterMatch(node.children, filter);
      if (filter && !nameMatch && !childrenMatch) return;

      var nodePath = parentPath ? parentPath + "/" + node.name : node.name;

      var nodeEl = document.createElement("div");
      nodeEl.className = "tree-ou-node";

      var hasChildren = node.children && node.children.length > 0;

      // Строка узла
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
      label.innerHTML = escapeHtml(node.name)
        + " <span class=\"tree-group-count\">(" + node.count + "/" + node.total + ")</span>";

      label.onclick = function (e) {
        e.stopPropagation();
        loadMembers(nodePath, domainKey);
      };

      if (nodePath === selectedPath && domainKey === selectedDomain) {
        label.classList.add("active");
      }

      row.appendChild(label);
      nodeEl.appendChild(row);

      // Вложенные дочерние
      if (hasChildren) {
        var childContainer = buildTreeNode(node.children, nodePath, domainKey, filter);
        childContainer.style.display = "none"; // свёрнуто по умолчанию

        // Если есть совпадение фильтра в потомках — развернуть
        if (filter && childrenMatch) {
          childContainer.style.display = "";
          if (row.querySelector(".tree-arrow")) {
            row.querySelector(".tree-arrow").innerHTML = "&#9660;";
          }
        }

        row.querySelector(".tree-arrow").onclick = function (e) {
          e.stopPropagation();
          var isHidden = childContainer.style.display === "none";
          childContainer.style.display = isHidden ? "" : "none";
          this.innerHTML = isHidden ? "&#9660;" : "&#9654;";
        };

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

  // ─── Рендер всего дерева ───
  function renderTree(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarTree.innerHTML = "";

    if (!treeData.length) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Нет данных AD</p>";
      return;
    }

    treeData.forEach(function (domain) {
      if (!domain.tree || !domain.tree.length) return;

      var domainEl = document.createElement("div");
      domainEl.className = "tree-domain";

      var header = document.createElement("div");
      header.className = "tree-domain-header";
      header.innerHTML = "<span class=\"tree-arrow\">&#9660;</span> "
        + escapeHtml(domain.city)
        + " <span class=\"tree-badge\">" + domain.total_users + " уч.</span>";

      var content = buildTreeNode(domain.tree, "", domain.key, filter);

      header.onclick = function () {
        domainEl.classList.toggle("collapsed");
        var arrow = header.querySelector(".tree-arrow");
        arrow.innerHTML = domainEl.classList.contains("collapsed") ? "&#9654;" : "&#9660;";
        content.style.display = domainEl.classList.contains("collapsed") ? "none" : "";
      };

      domainEl.appendChild(header);
      domainEl.appendChild(content);
      sidebarTree.appendChild(domainEl);
    });
  }

  // ─── Загрузка дерева ───
  async function loadTree() {
    try {
      var r = await fetch(API + "/api/structure/tree");
      var data = await r.json();
      treeData = data.domains || [];
      renderTree();
    } catch (e) {
      sidebarTree.innerHTML = "<p class=\"muted-text\">Ошибка: " + escapeHtml(e.message) + "</p>";
    }
  }

  // ─── Поиск ───
  ouSearch.addEventListener("input", function () {
    renderTree(ouSearch.value);
  });

  // ─── Экспорт XLSX ───
  var btnExport = document.getElementById("btn-export");
  if (btnExport) {
    btnExport.onclick = async function () {
      if (!cachedMembers.length) { alert("Нет данных для выгрузки"); return; }
      var ouName = (selectedPath || "ou").split("/").pop().replace(/[\\/:*?"<>|]/g, "_");
      try {
        var r = await fetch(API + "/api/export/table", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            columns: COLUMNS.map(function (c) { return { key: c.key, label: c.label }; }),
            rows: cachedMembers,
            filename: "OU_" + ouName + ".xlsx",
            sheet: ouName.substring(0, 31)
          })
        });
        if (!r.ok) { alert("Ошибка экспорта"); return; }
        var blob = await r.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "OU_" + ouName + ".xlsx";
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
  loadTree().then(function () {
    // Автооткрытие из URL: /structure?path=PATH&domain=KEY
    var params = new URLSearchParams(window.location.search);
    var pPath = params.get("path");
    var pDomain = params.get("domain");
    if (pPath && pDomain) {
      loadMembers(pPath, pDomain);
    }
  });
})();
