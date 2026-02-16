/**
 * Общие компоненты карточки пользователя.
 * Используется на страницах users.html и security.html.
 * Подключается ПОСЛЕ utils.js.
 */
window.CardUtils = (function () {
  var API = AppUtils.API;
  var esc = AppUtils.escapeHtml;

  // Callback для открытия полной карточки по ключу — устанавливается каждой страницей
  var _cardOpener = null;

  function setCardOpener(fn) { _cardOpener = fn; }

  // ─── Popup builder ───
  function createPopup(title, extraClass) {
    var overlay = document.createElement("div");
    overlay.className = "popup-overlay";
    var popup = document.createElement("div");
    popup.className = "popup-window" + (extraClass ? " " + extraClass : "");
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
    var closeBtn = header.querySelector(".popup-close");
    if (closeBtn) closeBtn.addEventListener("click", close);
    document.addEventListener("keydown", function onEsc(e) {
      if (e.key === "Escape") { close(); document.removeEventListener("keydown", onEsc); }
    });
    return { overlay: overlay, header: header, body: body, close: close };
  }

  // ─── Таблица полей карточки ───
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

  // ─── DN-ссылки ───
  function renderDnLinks(dnString) {
    if (!dnString) return "";
    var parts = dnString.split(";").map(function (s) { return s.trim(); }).filter(Boolean);
    if (!parts.length) return "";
    return parts.map(function (dn) {
      var cn = dn.match(/^CN=([^,]+)/i);
      var display = cn ? cn[1] : dn;
      return "<a class=\"ucard-link dn-link\" href=\"#\" data-dn=\"" + esc(dn) + "\">" + esc(display) + "</a>";
    }).join("; ");
  }

  // ─── Группы (простой список без ссылок — для security.js и popup-ов) ───
  function renderGroupsList(groupsStr) {
    if (!groupsStr) return "";
    var groups = groupsStr.split(";").map(function (g) { return g.trim(); }).filter(Boolean);
    return groups.map(function (g) { return esc(g); }).join("; ");
  }

  // ─── AD-секции (базовая версия с DN-ссылками) ───
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
      ["Адрес", a.street_address],
      ["Руководитель", { html: renderDnLinks(a.manager) }],
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
      ["whenCreated", a.when_created], ["whenChanged", a.when_changed],
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
      ["Подчинённые", { html: renderDnLinks(a.direct_reports) }],
      ["Управляемые объекты", { html: renderDnLinks(a.managed_objects) }],
      ["Основная группа", { html: renderDnLinks(a.primary_group) }],
    ]);
    if (a.info) {
      h += "<div class=\"ucard-ad-section-label\">Прочее</div>";
      h += renderFieldsTable([["Инфо", a.info]]);
    }
    return h;
  }

  // ─── Popup для объекта по DN ───
  function openDnPopup(dn, displayName) {
    AppUtils.fetchJSON(API + "/api/users/by-dn?dn=" + encodeURIComponent(dn))
      .then(function (data) {
        if (data.found && data.key && _cardOpener) {
          _cardOpener(data.key, data.display_name || displayName);
        } else {
          var p = createPopup(displayName || "Объект AD", "popup-window-wide");
          var cn = dn.match(/^CN=([^,]+)/i);
          var name = cn ? cn[1] : dn;
          var ous = [];
          var re = /OU=([^,]+)/gi;
          var match;
          while ((match = re.exec(dn)) !== null) ous.push(match[1]);
          ous.reverse();
          var html = "<table class=\"ucard-fields\">";
          html += "<tr><td class=\"ucard-label\">Имя (CN)</td><td>" + esc(name) + "</td></tr>";
          if (ous.length) html += "<tr><td class=\"ucard-label\">OU</td><td>" + esc(ous.join(" › ")) + "</td></tr>";
          html += "<tr><td class=\"ucard-label\">Полный DN</td><td class=\"ucard-val-long\">" + esc(dn) + "</td></tr>";
          html += "</table>";
          html += "<p class=\"muted-text\" style=\"margin-top:12px\">Объект не найден среди учётных записей пользователей в базе данных.</p>";
          p.body.innerHTML = html;
        }
      })
      .catch(function (e) {
        var p = createPopup(displayName || "Ошибка");
        p.body.innerHTML = "<p class=\"muted-text\">Ошибка: " + esc(e.message) + "</p>";
      });
  }

  // ─── Popup полной карточки пользователя ───
  function openUserCardPopup(key, displayName, renderAdFn) {
    var renderAd = renderAdFn || renderAdSections;
    var p = createPopup(displayName || "Карточка УЗ", "popup-window-wide");

    AppUtils.fetchJSON(API + "/api/users/card?key=" + encodeURIComponent(key))
      .then(function (data) {
        var titleEl = p.header.querySelector(".popup-title");
        if (titleEl) titleEl.textContent = data.fio || displayName || "Карточка УЗ";

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
            html += renderAd(a);
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

  // ─── Document-level handler для DN-ссылок внутри popup-ов ───
  document.addEventListener("click", function (e) {
    var link = e.target.closest(".popup-overlay [data-dn]");
    if (!link) return;
    e.preventDefault();
    openDnPopup(link.dataset.dn, link.textContent.trim());
  });

  return {
    createPopup: createPopup,
    renderFieldsTable: renderFieldsTable,
    renderDnLinks: renderDnLinks,
    renderGroupsList: renderGroupsList,
    renderAdSections: renderAdSections,
    openDnPopup: openDnPopup,
    openUserCardPopup: openUserCardPopup,
    setCardOpener: setCardOpener,
  };
})();
