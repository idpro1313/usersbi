(function () {
  var API = AppUtils.API;
  var esc = AppUtils.escapeHtml;

  var summaryEl = document.getElementById("sec-summary");
  var findingsEl = document.getElementById("sec-findings");

  var SEVERITY_LABEL = {
    critical: "Критич.",
    high: "Высокий",
    medium: "Средний",
    info: "Инфо"
  };
  var SEVERITY_CLASS = {
    critical: "sec-sev-critical",
    high: "sec-sev-high",
    medium: "sec-sev-medium",
    info: "sec-sev-info"
  };

  // ─── Загрузка данных ───
  async function load() {
    try {
      var r = await fetch(API + "/api/security/findings");
      var data = await r.json();
      renderSummary(data);
      renderFindings(data.findings);
    } catch (e) {
      summaryEl.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
    }
  }

  // ─── Сводка ───
  function renderSummary(data) {
    var cards = [
      { label: "Всего УЗ", value: data.total_accounts, cls: "" },
      { label: "Активных", value: data.total_enabled, cls: "" },
      { label: "Критичных", value: data.critical_count, cls: data.critical_count > 0 ? "sec-card-critical" : "" },
      { label: "Высоких", value: data.high_count, cls: data.high_count > 0 ? "sec-card-high" : "" },
      { label: "Всего замечаний", value: data.total_issues, cls: data.total_issues > 0 ? "sec-card-warn" : "sec-card-ok" },
    ];
    var html = "";
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      html += "<div class=\"sec-card " + c.cls + "\">";
      html += "<div class=\"sec-card-value\">" + c.value + "</div>";
      html += "<div class=\"sec-card-label\">" + esc(c.label) + "</div>";
      html += "</div>";
    }
    summaryEl.innerHTML = html;
  }

  // ─── Категории ───
  function renderFindings(findings) {
    var html = "";
    for (var i = 0; i < findings.length; i++) {
      var f = findings[i];
      var sevCls = SEVERITY_CLASS[f.severity] || "";
      var sevLabel = SEVERITY_LABEL[f.severity] || f.severity;
      var hasItems = f.count > 0;
      var collapsed = f.count > 20;

      html += "<div class=\"sec-finding " + sevCls + (hasItems ? "" : " sec-finding-ok") + "\" data-id=\"" + f.id + "\">";
      html += "<div class=\"sec-finding-header\" data-toggle=\"" + f.id + "\">";
      html += "<span class=\"sec-finding-sev\">" + esc(sevLabel) + "</span>";
      html += "<span class=\"sec-finding-title\">" + esc(f.title) + "</span>";
      html += "<span class=\"sec-finding-count\">" + f.count + "</span>";
      html += "<span class=\"sec-finding-arrow\">" + (hasItems ? "▸" : "✓") + "</span>";
      html += "</div>";
      html += "<div class=\"sec-finding-desc\">" + esc(f.description) + "</div>";

      if (hasItems) {
        html += "<div class=\"sec-finding-body\" id=\"sec-body-" + f.id + "\"" + (collapsed ? " style=\"display:none\"" : "") + ">";
        html += renderTable(f.items, f.extra_columns);
        html += "</div>";
      }

      html += "</div>";
    }
    findingsEl.innerHTML = html;

    // Toggle collapse
    findingsEl.addEventListener("click", function (e) {
      var header = e.target.closest("[data-toggle]");
      if (!header) return;
      var id = header.dataset.toggle;
      var body = document.getElementById("sec-body-" + id);
      if (!body) return;
      var arrow = header.querySelector(".sec-finding-arrow");
      if (body.style.display === "none") {
        body.style.display = "";
        if (arrow) arrow.textContent = "▾";
      } else {
        body.style.display = "none";
        if (arrow) arrow.textContent = "▸";
      }
    });

    // Click → popup карточки
    findingsEl.addEventListener("click", function (e) {
      var link = e.target.closest("[data-user-key]");
      if (!link) return;
      e.preventDefault();
      var key = link.dataset.userKey;
      if (key) openUserPopup(key, link.textContent.trim());
    });
  }

  // ─── Popup карточки пользователя ───
  function createPopup(title) {
    var overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    var popup = document.createElement("div");
    popup.className = "popup-window popup-window-wide";
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
    function close() { overlay.remove(); }
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    header.querySelector(".popup-close").addEventListener("click", close);
    document.addEventListener("keydown", function onEsc(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
    });
    return { overlay: overlay, header: header, body: body, close: close };
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

  function renderGroupsList(groupsStr) {
    if (!groupsStr) return "";
    var groups = groupsStr.split(";").map(function (g) { return g.trim(); }).filter(Boolean);
    return groups.map(function (g) { return esc(g); }).join("; ");
  }

  function renderAdSections(a) {
    var h = "";
    h += "<div class=\"ucard-ad-section-label\">Основные</div>";
    h += renderFieldsTable([
      ["ФИО", a.display_name], ["Имя", a.given_name], ["Фамилия", a.surname_ad],
      ["UPN", a.upn], ["Email", a.email],
      ["Телефон", a.phone], ["Мобильный", a.mobile],
      ["Описание", a.description],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Должность</div>";
    h += renderFieldsTable([
      ["Должность", a.title], ["Отдел", a.department], ["Компания", a.company],
      ["Тип сотрудника", a.employee_type], ["Расположение", a.location],
      ["Адрес", a.street_address], ["Руководитель", a.manager_name || a.manager],
      ["Таб. номер", a.employee_number],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Статус</div>";
    h += renderFieldsTable([
      ["Активна", a.enabled], ["Заблокирована", a.locked_out],
      ["Время блокировки", a.account_lockout_time],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Пароль</div>";
    h += renderFieldsTable([
      ["Смена пароля", a.password_last_set], ["Пароль сменён", a.pwd_last_set],
      ["Треб. смена пароля", a.must_change_password],
      ["Пароль просрочен", a.password_expired],
      ["Бессрочный пароль", a.password_never_expires],
      ["Пароль не требуется", a.password_not_required],
      ["Запрет смены пароля", a.cannot_change_password],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Срок действия</div>";
    h += renderFieldsTable([
      ["Срок УЗ", a.account_expires], ["Дата окончания", a.account_expiration_date],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Активность</div>";
    h += renderFieldsTable([
      ["Последний вход", a.last_logon_date],
      ["Посл. вход (timestamp)", a.last_logon_timestamp],
      ["Кол-во входов", a.logon_count],
      ["Посл. ошибка пароля", a.last_bad_password_attempt],
      ["Кол-во ошибок", a.bad_logon_count],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Жизненный цикл</div>";
    h += renderFieldsTable([
      ["Создана", a.created_date], ["Изменена", a.modified_date],
      ["Дата выгрузки", a.exported_at],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Безопасность</div>";
    h += renderFieldsTable([
      ["Делегирование", a.trusted_for_delegation],
      ["Протокольный переход", a.trusted_to_auth_for_delegation],
      ["Запрет делегирования", a.account_not_delegated],
      ["Без Kerberos Pre-Auth", a.does_not_require_preauth],
      ["Обратимое шифрование", a.allow_reversible_password_encryption],
      ["Только смарт-карта", a.smartcard_logon_required],
      ["Защита от удаления", a.protected_from_accidental_deletion],
      ["UAC", a.user_account_control],
      ["SPN", a.service_principal_names],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Идентификаторы</div>";
    h += renderFieldsTable([
      ["ObjectGUID", a.object_guid], ["SID", a.sid],
      ["CanonicalName", a.canonical_name],
      ["DN", a.distinguished_name],
      ["StaffUUID", a.staff_uuid],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Профиль</div>";
    h += renderFieldsTable([
      ["Рабочие станции", a.logon_workstations],
      ["Диск", a.home_drive], ["Дом. каталог", a.home_directory],
      ["Профиль", a.profile_path], ["Скрипт", a.script_path],
    ]);
    h += "<div class=\"ucard-ad-section-label\">Связи</div>";
    h += renderFieldsTable([
      ["Группы", { html: renderGroupsList(a.groups) }],
      ["Подчинённые", a.direct_reports],
      ["Управляемые объекты", a.managed_objects],
      ["Основная группа", a.primary_group],
    ]);
    if (a.info) {
      h += "<div class=\"ucard-ad-section-label\">Прочее</div>";
      h += renderFieldsTable([["Инфо", a.info]]);
    }
    return h;
  }

  function openUserPopup(key, displayName) {
    var p = createPopup(displayName || "Карточка УЗ");

    fetch(API + "/api/users/card?key=" + encodeURIComponent(key))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        p.header.querySelector(".popup-title").textContent = data.fio || displayName || "Карточка УЗ";

        var html = "";

        // Шапка
        html += "<div class=\"ucard-header\">";
        html += "<h2 class=\"ucard-fio\">" + esc(data.fio || "—") + "</h2>";
        if (data.staff_uuid) html += "<span class=\"ucard-uuid\">StaffUUID: " + esc(data.staff_uuid) + "</span>";
        if (data.logins && data.logins.length) html += "<span class=\"ucard-logins\">Логины: " + esc(data.logins.join(", ")) + "</span>";
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
            html += renderAdSections(a);
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
              ["Последний вход", m.last_login], ["Аутентификаторы", m.authenticators],
            ]);
            html += "</div>";
          }
          html += "</div>";
        }

        p.body.innerHTML = html;
      })
      .catch(function (e) {
        p.body.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
      });
  }

  function renderTable(items, extraCols) {
    var baseCols = [
      { key: "display_name", label: "ФИО" },
      { key: "login", label: "Логин" },
      { key: "domain", label: "Домен" },
      { key: "enabled", label: "Активна" },
    ];
    var cols = baseCols.concat(extraCols || []);

    var html = "<table class=\"data-table sec-table\">";
    html += "<thead><tr><th>#</th>";
    for (var c = 0; c < cols.length; c++) html += "<th>" + esc(cols[c].label) + "</th>";
    html += "</tr></thead><tbody>";

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var rowCls = item.enabled === "Нет" ? " class=\"row-inactive\"" : "";
      html += "<tr" + rowCls + ">";
      html += "<td class=\"col-num\">" + (i + 1) + "</td>";
      for (var c2 = 0; c2 < cols.length; c2++) {
        var val = item[cols[c2].key] || "";
        if (cols[c2].key === "display_name" && item.key) {
          html += "<td><a href=\"#\" class=\"ucard-link\" data-user-key=\"" + esc(item.key) + "\">" + esc(val || item.login) + "</a></td>";
        } else {
          html += "<td>" + esc(val) + "</td>";
        }
      }
      html += "</tr>";
    }

    html += "</tbody></table>";
    return html;
  }

  load();
})();
