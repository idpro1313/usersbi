(function () {
  var API = AppUtils.API;
  var esc = AppUtils.escapeHtml;

  // ─── Состояние ───
  var allUsers = [];
  var selectedKey = null;

  // ─── DOM ───
  var sidebarList = document.getElementById("sidebar-list");
  var sidebarInfo = document.getElementById("sidebar-info");
  var userSearch = document.getElementById("user-search");
  var cardWrap = document.getElementById("user-card");

  // ─── Рендер списка пользователей (с event delegation) ───
  function renderList(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarList.innerHTML = "";

    var filtered = allUsers;
    if (filter) {
      filtered = allUsers.filter(function (u) {
        return [u.fio, u.staff_uuid].concat(u.logins).join(" ").toLowerCase().indexOf(filter) !== -1;
      });
    }

    sidebarInfo.textContent = "Найдено: " + filtered.length + " из " + allUsers.length;

    if (!filtered.length) {
      sidebarList.innerHTML = "<p class=\"muted-text\">Нет результатов</p>";
      return;
    }

    var fragment = document.createDocumentFragment();
    var LIMIT = 500;
    var shown = Math.min(filtered.length, LIMIT);

    for (var i = 0; i < shown; i++) {
      var u = filtered[i];
      var item = document.createElement("div");
      item.className = "user-list-item";
      if (u.all_disabled) item.classList.add("user-disabled");
      item.dataset.key = u.key;
      if (u.key === selectedKey) item.classList.add("active");

      var nameLine = esc(u.fio || u.logins[0] || u.staff_uuid || "—");
      var metaLine = [];
      if (u.logins.length) metaLine.push(u.logins.join(", "));
      if (u.staff_uuid) metaLine.push("UUID: " + u.staff_uuid);

      item.innerHTML =
        "<div class=\"user-item-name\">" + nameLine + "</div>" +
        "<div class=\"user-item-meta\">" + esc(metaLine.join(" · ")) + "</div>" +
        "<div class=\"user-item-sources\">" + esc(u.sources.join(", ")) + "</div>";

      fragment.appendChild(item);
    }

    sidebarList.appendChild(fragment);

    if (filtered.length > LIMIT) {
      var more = document.createElement("p");
      more.className = "muted-text";
      more.textContent = "Показано " + LIMIT + " из " + filtered.length + " — уточните поиск";
      sidebarList.appendChild(more);
    }
  }

  // Event delegation для клика по пользователю
  sidebarList.addEventListener("click", function (e) {
    var item = e.target.closest(".user-list-item");
    if (item && item.dataset.key) {
      loadCard(item.dataset.key);
    }
  });

  // ─── Загрузка списка ───
  async function loadList() {
    try {
      var r = await fetch(API + "/api/users/list");
      var data = await r.json();
      allUsers = data.users || [];
      renderList();
    } catch (e) {
      sidebarList.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  function highlightSelected() {
    var items = sidebarList.querySelectorAll(".user-list-item");
    for (var i = 0; i < items.length; i++) {
      if (items[i].dataset.key === selectedKey) {
        items[i].classList.add("active");
      } else {
        items[i].classList.remove("active");
      }
    }
  }

  // ─── Загрузка карточки ───
  async function loadCard(key) {
    selectedKey = key;
    highlightSelected();
    cardWrap.innerHTML = "<p class=\"muted-text\">Загрузка…</p>";
    try {
      var r = await fetch(API + "/api/users/card?key=" + encodeURIComponent(key));
      var data = await r.json();
      renderCard(data);
    } catch (e) {
      cardWrap.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  // ─── Рендер карточки ───
  function renderCard(data) {
    var html = "";

    html += "<div class=\"ucard-header\">";
    html += "<h2 class=\"ucard-fio\">" + esc(data.fio || "—") + "</h2>";
    if (data.staff_uuid) {
      html += "<span class=\"ucard-uuid\">StaffUUID: " + esc(data.staff_uuid) + "</span>";
    }
    if (data.logins && data.logins.length) {
      html += "<span class=\"ucard-logins\">Логины: " + esc(data.logins.join(", ")) + "</span>";
    }
    // Сводные поля: город, локация, подразделение DP, RM
    var summaryParts = [];
    if (data.city) summaryParts.push(["Город", data.city]);
    if (data.hub) summaryParts.push(["Локация", data.hub]);
    if (data.dp_unit) summaryParts.push(["Подразделение DP", data.dp_unit]);
    if (data.rm) summaryParts.push(["RM", data.rm]);
    if (summaryParts.length) {
      html += "<div class=\"ucard-summary\">";
      for (var s = 0; s < summaryParts.length; s++) {
        html += "<span class=\"ucard-summary-item\"><b>" + esc(summaryParts[s][0]) + ":</b> " + esc(summaryParts[s][1]) + "</span>";
      }
      html += "</div>";
    }
    html += "</div>";

    // Кадры
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">Кадры (Develonica.People)</h3>";
    if (data.people) {
      html += renderFieldsTable([
        ["ФИО", data.people.fio], ["Email", data.people.email],
        ["Телефон", data.people.phone], ["Подразделение", data.people.unit],
        ["Хаб", data.people.hub], ["Статус", data.people.employment_status],
        ["Руководитель", data.people.unit_manager], ["Формат работы", data.people.work_format],
        ["HR BP", data.people.hr_bp], ["StaffUUID", data.people.staff_uuid],
      ]);
    } else {
      html += "<p class=\"muted-text\">Нет данных в кадрах</p>";
    }
    html += "</div>";

    // AD
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">Учётные записи AD (" + data.ad.length + ")</h3>";
    if (data.ad.length) {
      for (var i = 0; i < data.ad.length; i++) {
        var a = data.ad[i];
        var inactive = a.enabled === "Нет";
        html += "<div class=\"ucard-ad-block" + (inactive ? " uz-inactive" : "") + "\">";
        html += "<div class=\"ucard-ad-domain\">" + esc(a.domain) + " — " + esc(a.login) + "</div>";
        html += renderFieldsTable([
          ["ФИО", a.display_name], ["Email", a.email],
          ["Телефон", a.phone], ["Мобильный", a.mobile],
          ["Активна", a.enabled], ["Смена пароля", a.password_last_set],
          ["Срок УЗ", a.account_expires], ["Должность", a.title],
          ["Отдел", a.department], ["Компания", a.company],
          ["Расположение", a.location],
          ["Руководитель", { html: renderManagerLink(a.manager, a.manager_key, a.manager_name) }],
          ["Таб. номер", a.employee_number],
          ["OU", { html: renderOuLink(a.distinguished_name, a.ad_source) }],
          ["Группы", { html: renderGroupLinks(a.groups, a.ad_source) }],
          ["Инфо", a.info], ["StaffUUID", a.staff_uuid],
        ]);
        html += "</div>";
      }
    } else {
      html += "<p class=\"muted-text\">Нет учётных записей в AD</p>";
    }
    html += "</div>";

    // MFA
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">MFA (" + data.mfa.length + ")</h3>";
    if (data.mfa.length) {
      for (var j = 0; j < data.mfa.length; j++) {
        var m = data.mfa[j];
        html += "<div class=\"ucard-mfa-block\">";
        html += renderFieldsTable([
          ["Identity", m.identity], ["ФИО", m.name],
          ["Email", m.email], ["Телефон", m.phones],
          ["Статус", m.status], ["Зарегистрирован", m.is_enrolled],
          ["Аутентификаторы", m.authenticators], ["Последний вход", m.last_login],
          ["Создан", m.created_at], ["Группы MFA", m.mfa_groups],
          ["LDAP", m.ldap],
        ]);
        html += "</div>";
      }
    } else {
      html += "<p class=\"muted-text\">Нет записи MFA</p>";
    }
    html += "</div>";

    // Возможные совпадения
    if (data.matches && data.matches.length) {
      html += "<div class=\"ucard-section\">";
      html += "<h3 class=\"ucard-section-title ucard-matches-title\">Возможные совпадения (" + data.matches.length + ")</h3>";
      html += "<table class=\"data-table ucard-matches-table\">";
      html += "<thead><tr>";
      html += "<th>Причина</th><th>Источник</th><th>ФИО</th><th>Email</th>";
      html += "<th>Логин</th><th>StaffUUID</th><th>Активна</th>";
      html += "</tr></thead><tbody>";
      for (var k = 0; k < data.matches.length; k++) {
        var mt = data.matches[k];
        html += "<tr>";
        html += "<td><span class=\"match-reason\">" + esc(mt.reason) + "</span></td>";
        html += "<td>" + esc(mt.source) + "</td>";
        html += "<td>" + esc(mt.fio) + "</td>";
        html += "<td>" + esc(mt.email) + "</td>";
        html += "<td>" + esc(mt.login) + "</td>";
        html += "<td>" + esc(mt.staff_uuid) + "</td>";
        html += "<td>" + esc(mt.enabled) + "</td>";
        html += "</tr>";
      }
      html += "</tbody></table>";
      html += "</div>";
    }

    cardWrap.innerHTML = html;
  }

  function renderGroupLinks(groupsStr, adSource) {
    if (!groupsStr) return "";
    var groups = groupsStr.split(";").map(function (g) { return g.trim(); }).filter(Boolean);
    if (!groups.length) return "";
    return groups.map(function (g) {
      var url = "/groups?domain=" + encodeURIComponent(adSource) + "&group=" + encodeURIComponent(g);
      return "<a class=\"ucard-link\" href=\"#\" data-popup-url=\"" + esc(url) + "\" data-popup-type=\"group\" data-popup-domain=\"" + esc(adSource) + "\" data-popup-name=\"" + esc(g) + "\">" + esc(g) + "</a>";
    }).join("; ");
  }

  function renderManagerLink(managerDn, managerKey, managerName) {
    if (!managerDn) return "";
    // Извлекаем CN из DN для отображения
    var displayName = managerName || "";
    if (!displayName) {
      var cnMatch = managerDn.match(/^CN=([^,]+)/i);
      displayName = cnMatch ? cnMatch[1] : managerDn;
    }
    if (!managerKey) {
      return esc(displayName);
    }
    return "<a class=\"ucard-link\" href=\"#\" data-popup-type=\"manager\" data-manager-key=\"" + esc(managerKey) + "\">" + esc(displayName) + "</a>";
  }

  function renderOuLink(dn, adSource) {
    if (!dn) return "";
    var ous = [];
    var re = /OU=([^,]+)/gi;
    var match;
    while ((match = re.exec(dn)) !== null) {
      ous.push(match[1]);
    }
    if (!ous.length) return esc(dn);
    ous.reverse();
    var path = ous.join("/");
    var url = "/structure?domain=" + encodeURIComponent(adSource) + "&path=" + encodeURIComponent(path);
    return "<a class=\"ucard-link\" href=\"#\" data-popup-url=\"" + esc(url) + "\" data-popup-type=\"ou\" data-popup-domain=\"" + esc(adSource) + "\" data-popup-name=\"" + esc(path) + "\">" + esc(ous.join(" › ")) + "</a>";
  }

  function renderFieldsTable(pairs) {
    var rows = "";
    for (var i = 0; i < pairs.length; i++) {
      var label = pairs[i][0];
      var value = pairs[i][1];
      if (!value) continue;
      var isHtml = value && typeof value === "object" && value.html !== undefined;
      var rawHtml = isHtml ? value.html : "";
      var textVal = isHtml ? "" : (value || "");
      if (!rawHtml && !textVal) continue;
      var valClass = "";
      if (!isHtml && textVal.length > 80) valClass = " class=\"ucard-val-long\"";
      if (isHtml) valClass = " class=\"ucard-val-long\"";
      var cellContent = isHtml ? rawHtml : esc(textVal);
      rows += "<tr><td class=\"ucard-label\">" + esc(label) + "</td><td" + valClass + ">" + cellContent + "</td></tr>";
    }
    if (!rows) return "<p class=\"muted-text\">Нет данных</p>";
    return "<table class=\"ucard-fields\">" + rows + "</table>";
  }

  // ─── Popup для групп / OU / руководитель ───
  cardWrap.addEventListener("click", function (e) {
    var link = e.target.closest("[data-popup-type]");
    if (!link) return;
    e.preventDefault();
    var type = link.dataset.popupType;
    if (type === "manager") {
      openManagerPopup(link.dataset.managerKey);
      return;
    }
    var domain = link.dataset.popupDomain;
    var name = link.dataset.popupName;
    openMembersPopup(type, domain, name);
  });

  function openMembersPopup(type, domain, name) {
    // Определяем API-URL
    var apiUrl;
    var title;
    if (type === "group") {
      apiUrl = API + "/api/groups/members?domain=" + encodeURIComponent(domain) + "&group=" + encodeURIComponent(name);
      title = "Группа: " + name;
    } else {
      apiUrl = API + "/api/structure/members?domain=" + encodeURIComponent(domain) + "&path=" + encodeURIComponent(name);
      title = "OU: " + name.replace(/\//g, " › ");
    }

    // Создаём overlay
    var overlay = document.createElement("div");
    overlay.className = "popup-overlay";

    var popup = document.createElement("div");
    popup.className = "popup-window";

    var header = document.createElement("div");
    header.className = "popup-header";
    header.innerHTML =
      "<h3 class=\"popup-title\">" + esc(title) + "</h3>" +
      "<button class=\"popup-close btn-icon\" title=\"Закрыть\">" +
        "<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\">" +
          "<line x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"/><line x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"/>" +
        "</svg>" +
      "</button>";

    var body = document.createElement("div");
    body.className = "popup-body";
    body.innerHTML = "<p class=\"muted-text\">Загрузка…</p>";

    popup.appendChild(header);
    popup.appendChild(body);
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Закрытие
    function close() { overlay.remove(); }
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
    header.querySelector(".popup-close").addEventListener("click", close);
    document.addEventListener("keydown", function onEsc(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
    });

    // Загружаем данные
    fetch(apiUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var members = data.members || [];
        if (!members.length) {
          body.innerHTML = "<p class=\"muted-text\">Нет участников</p>";
          return;
        }

        var cols = [
          { key: "display_name", label: "ФИО" },
          { key: "login",        label: "Логин" },
          { key: "email",        label: "Email" },
          { key: "enabled",      label: "Активна" },
          { key: "password_last_set", label: "Смена пароля" },
          { key: "title",        label: "Должность" },
          { key: "department",   label: "Отдел" },
          { key: "company",      label: "Компания" },
        ];

        var tbl = "<p class=\"popup-count\">Участников: " + members.length + "</p>";
        tbl += "<table class=\"data-table popup-table\"><thead><tr>";
        for (var c = 0; c < cols.length; c++) {
          tbl += "<th>" + esc(cols[c].label) + "</th>";
        }
        tbl += "</tr></thead><tbody>";

        for (var i = 0; i < members.length; i++) {
          var m = members[i];
          var rowCls = (m.enabled || "").toLowerCase() === "нет" ? " class=\"row-inactive\"" : "";
          tbl += "<tr" + rowCls + ">";
          for (var c2 = 0; c2 < cols.length; c2++) {
            tbl += "<td>" + esc(m[cols[c2].key] || "") + "</td>";
          }
          tbl += "</tr>";
        }
        tbl += "</tbody></table>";
        body.innerHTML = tbl;
      })
      .catch(function (e) {
        body.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
      });
  }

  // ─── Popup карточки руководителя ───
  function openManagerPopup(managerKey) {
    var overlay = document.createElement("div");
    overlay.className = "popup-overlay";

    var popup = document.createElement("div");
    popup.className = "popup-window popup-window-wide";

    var header = document.createElement("div");
    header.className = "popup-header";
    header.innerHTML =
      "<h3 class=\"popup-title\">Карточка руководителя</h3>" +
      "<button class=\"popup-close btn-icon\" title=\"Закрыть\">" +
        "<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\">" +
          "<line x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"/><line x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"/>" +
        "</svg>" +
      "</button>";

    var body = document.createElement("div");
    body.className = "popup-body";
    body.innerHTML = "<p class=\"muted-text\">Загрузка…</p>";

    popup.appendChild(header);
    popup.appendChild(body);
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    function close() { overlay.remove(); }
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
    header.querySelector(".popup-close").addEventListener("click", close);
    document.addEventListener("keydown", function onEsc(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
    });

    fetch(API + "/api/users/card?key=" + encodeURIComponent(managerKey))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        header.querySelector(".popup-title").textContent =
          "Руководитель: " + (data.fio || managerKey);

        var html = "";

        // Заголовок
        html += "<div class=\"ucard-header\">";
        html += "<h2 class=\"ucard-fio\">" + esc(data.fio || "—") + "</h2>";
        if (data.staff_uuid) html += "<span class=\"ucard-uuid\">StaffUUID: " + esc(data.staff_uuid) + "</span>";
        if (data.logins && data.logins.length) html += "<span class=\"ucard-logins\">Логины: " + esc(data.logins.join(", ")) + "</span>";
        // Сводные поля
        var sp = [];
        if (data.city) sp.push(["Город", data.city]);
        if (data.hub) sp.push(["Локация", data.hub]);
        if (data.dp_unit) sp.push(["Подразделение DP", data.dp_unit]);
        if (data.rm) sp.push(["RM", data.rm]);
        if (sp.length) {
          html += "<div class=\"ucard-summary\">";
          for (var si = 0; si < sp.length; si++) {
            html += "<span class=\"ucard-summary-item\"><b>" + esc(sp[si][0]) + ":</b> " + esc(sp[si][1]) + "</span>";
          }
          html += "</div>";
        }
        html += "</div>";

        // Кадры
        if (data.people) {
          html += "<div class=\"ucard-section\">";
          html += "<h3 class=\"ucard-section-title\">Кадры</h3>";
          html += renderFieldsTable([
            ["ФИО", data.people.fio], ["Email", data.people.email],
            ["Телефон", data.people.phone], ["Подразделение", data.people.unit],
            ["Хаб", data.people.hub], ["Статус", data.people.employment_status],
            ["RM", data.people.unit_manager],
          ]);
          html += "</div>";
        }

        // AD
        if (data.ad && data.ad.length) {
          html += "<div class=\"ucard-section\">";
          html += "<h3 class=\"ucard-section-title\">Учётные записи AD (" + data.ad.length + ")</h3>";
          for (var i = 0; i < data.ad.length; i++) {
            var a = data.ad[i];
            var inactive = a.enabled === "Нет";
            html += "<div class=\"ucard-ad-block" + (inactive ? " uz-inactive" : "") + "\">";
            html += "<div class=\"ucard-ad-domain\">" + esc(a.domain) + " — " + esc(a.login) + "</div>";
            html += renderFieldsTable([
              ["ФИО", a.display_name], ["Email", a.email],
              ["Активна", a.enabled], ["Должность", a.title],
              ["Отдел", a.department], ["Компания", a.company],
              ["Город", a.location],
            ]);
            html += "</div>";
          }
          html += "</div>";
        }

        // MFA
        if (data.mfa && data.mfa.length) {
          html += "<div class=\"ucard-section\">";
          html += "<h3 class=\"ucard-section-title\">MFA (" + data.mfa.length + ")</h3>";
          for (var j = 0; j < data.mfa.length; j++) {
            var m = data.mfa[j];
            html += "<div class=\"ucard-mfa-block\">";
            html += renderFieldsTable([
              ["Identity", m.identity], ["Статус", m.status],
              ["Последний вход", m.last_login],
            ]);
            html += "</div>";
          }
          html += "</div>";
        }

        body.innerHTML = html;
      })
      .catch(function (e) {
        body.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
      });
  }

  userSearch.addEventListener("input", function () {
    renderList(userSearch.value);
  });

  loadList();
})();
