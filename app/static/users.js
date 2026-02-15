(function () {
  var API = "";

  // ─── Состояние ───
  var allUsers = [];
  var selectedKey = null;

  // ─── DOM ───
  var sidebarList = document.getElementById("sidebar-list");
  var sidebarInfo = document.getElementById("sidebar-info");
  var userSearch = document.getElementById("user-search");
  var cardWrap = document.getElementById("user-card");

  // ─── Утилиты ───
  function esc(s) {
    if (s == null) return "";
    var t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  }

  // ─── Рендер списка пользователей ───
  function renderList(filter) {
    filter = (filter || "").trim().toLowerCase();
    sidebarList.innerHTML = "";

    var filtered = allUsers;
    if (filter) {
      filtered = allUsers.filter(function (u) {
        var haystack = [u.fio, u.staff_uuid].concat(u.logins).join(" ").toLowerCase();
        return haystack.indexOf(filter) !== -1;
      });
    }

    sidebarInfo.textContent = "Найдено: " + filtered.length + " из " + allUsers.length;

    if (!filtered.length) {
      sidebarList.innerHTML = "<p class=\"muted-text\">Нет результатов</p>";
      return;
    }

    var fragment = document.createDocumentFragment();
    // Показываем порциями для производительности
    var LIMIT = 500;
    var shown = Math.min(filtered.length, LIMIT);

    for (var i = 0; i < shown; i++) {
      var u = filtered[i];
      var item = document.createElement("div");
      item.className = "user-list-item";
      item.dataset.key = u.key;
      if (u.key === selectedKey) item.classList.add("active");

      var nameLine = esc(u.fio || u.logins[0] || u.staff_uuid || "—");
      var metaLine = [];
      if (u.logins.length) metaLine.push(u.logins.join(", "));
      if (u.staff_uuid) metaLine.push("UUID: " + u.staff_uuid);
      var sources = u.sources.join(", ");

      item.innerHTML =
        "<div class=\"user-item-name\">" + nameLine + "</div>" +
        "<div class=\"user-item-meta\">" + esc(metaLine.join(" · ")) + "</div>" +
        "<div class=\"user-item-sources\">" + esc(sources) + "</div>";

      (function (key) {
        item.onclick = function () { loadCard(key); };
      })(u.key);

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

  // ─── Подсветка выбранного ───
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

    // ─── Заголовок ───
    html += "<div class=\"ucard-header\">";
    html += "<h2 class=\"ucard-fio\">" + esc(data.fio || "—") + "</h2>";
    if (data.staff_uuid) {
      html += "<span class=\"ucard-uuid\">StaffUUID: " + esc(data.staff_uuid) + "</span>";
    }
    if (data.logins && data.logins.length) {
      html += "<span class=\"ucard-logins\">Логины: " + esc(data.logins.join(", ")) + "</span>";
    }
    html += "</div>";

    // ─── Кадры ───
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">Кадры (Develonica.People)</h3>";
    if (data.people) {
      html += renderFieldsTable([
        ["ФИО", data.people.fio],
        ["Email", data.people.email],
        ["Телефон", data.people.phone],
        ["Подразделение", data.people.unit],
        ["Хаб", data.people.hub],
        ["Статус", data.people.employment_status],
        ["Руководитель", data.people.unit_manager],
        ["Формат работы", data.people.work_format],
        ["HR BP", data.people.hr_bp],
        ["StaffUUID", data.people.staff_uuid],
      ]);
    } else {
      html += "<p class=\"muted-text\">Нет данных в кадрах</p>";
    }
    html += "</div>";

    // ─── УЗ в AD ───
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">Учётные записи AD (" + data.ad.length + ")</h3>";
    if (data.ad.length) {
      for (var i = 0; i < data.ad.length; i++) {
        var a = data.ad[i];
        var inactive = a.enabled === "Нет";
        html += "<div class=\"ucard-ad-block" + (inactive ? " uz-inactive" : "") + "\">";
        html += "<div class=\"ucard-ad-domain\">" + esc(a.domain) + " — " + esc(a.login) + "</div>";
        html += renderFieldsTable([
          ["ФИО", a.display_name],
          ["Email", a.email],
          ["Телефон", a.phone],
          ["Мобильный", a.mobile],
          ["Активна", a.enabled],
          ["Смена пароля", a.password_last_set],
          ["Срок УЗ", a.account_expires],
          ["Должность", a.title],
          ["Отдел", a.department],
          ["Компания", a.company],
          ["Расположение", a.location],
          ["Руководитель", a.manager],
          ["Таб. номер", a.employee_number],
          ["OU", { html: renderOuLink(a.distinguished_name, a.ad_source) }],
          ["Группы", { html: renderGroupLinks(a.groups, a.ad_source) }],
          ["Инфо", a.info],
          ["StaffUUID", a.staff_uuid],
        ]);
        html += "</div>";
      }
    } else {
      html += "<p class=\"muted-text\">Нет учётных записей в AD</p>";
    }
    html += "</div>";

    // ─── MFA ───
    html += "<div class=\"ucard-section\">";
    html += "<h3 class=\"ucard-section-title\">MFA (" + data.mfa.length + ")</h3>";
    if (data.mfa.length) {
      for (var j = 0; j < data.mfa.length; j++) {
        var m = data.mfa[j];
        html += "<div class=\"ucard-mfa-block\">";
        html += renderFieldsTable([
          ["Identity", m.identity],
          ["ФИО", m.name],
          ["Email", m.email],
          ["Телефон", m.phones],
          ["Статус", m.status],
          ["Зарегистрирован", m.is_enrolled],
          ["Аутентификаторы", m.authenticators],
          ["Последний вход", m.last_login],
          ["Создан", m.created_at],
          ["Группы MFA", m.mfa_groups],
          ["LDAP", m.ldap],
        ]);
        html += "</div>";
      }
    } else {
      html += "<p class=\"muted-text\">Нет записи MFA</p>";
    }
    html += "</div>";

    cardWrap.innerHTML = html;
  }

  // ─── Ссылки на группы ───
  function renderGroupLinks(groupsStr, adSource) {
    if (!groupsStr) return "";
    var groups = groupsStr.split(";").map(function (g) { return g.trim(); }).filter(Boolean);
    if (!groups.length) return "";
    return groups.map(function (g) {
      var href = "/groups?domain=" + encodeURIComponent(adSource) + "&group=" + encodeURIComponent(g);
      return "<a class=\"ucard-link\" href=\"" + href + "\">" + esc(g) + "</a>";
    }).join("; ");
  }

  // ─── Ссылка на OU ───
  function renderOuLink(dn, adSource) {
    if (!dn) return "";
    // Извлекаем OU= из DN (от листа к корню), переворачиваем
    var ous = [];
    var re = /OU=([^,]+)/gi;
    var match;
    while ((match = re.exec(dn)) !== null) {
      ous.push(match[1]);
    }
    if (!ous.length) return esc(dn);
    ous.reverse(); // от корня к листу
    var path = ous.join("/");
    var href = "/structure?domain=" + encodeURIComponent(adSource) + "&path=" + encodeURIComponent(path);
    return "<a class=\"ucard-link\" href=\"" + href + "\">" + esc(ous.join(" › ")) + "</a>";
  }

  function renderFieldsTable(pairs) {
    var rows = "";
    for (var i = 0; i < pairs.length; i++) {
      var label = pairs[i][0];
      var value = pairs[i][1];
      if (!value) continue;
      // Поддержка HTML-значений: { html: "..." }
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

  // ─── Поиск ───
  userSearch.addEventListener("input", function () {
    renderList(userSearch.value);
  });

  // ─── Инициализация ───
  loadList();
})();
