(function () {
  const API = "";

  // AD домены
  var adDomains = ["izhevsk", "kostroma", "moscow"];
  var adFiles = {};
  var adBtns = {};
  var adStatuses = {};
  adDomains.forEach(function (key) {
    adFiles[key] = document.getElementById("file-ad-" + key);
    adBtns[key] = document.getElementById("btn-ad-" + key);
    adStatuses[key] = document.getElementById("status-ad-" + key);
  });

  const fileMfa = document.getElementById("file-mfa");
  const filePeople = document.getElementById("file-people");
  const btnMfa = document.getElementById("btn-mfa");
  const btnPeople = document.getElementById("btn-people");
  const statusMfa = document.getElementById("status-mfa");
  const statusPeople = document.getElementById("status-people");
  const statsEl = document.getElementById("stats");
  const tbody = document.getElementById("tbody");
  const tableFooter = document.getElementById("table-footer");
  const btnRefresh = document.getElementById("btn-refresh");
  const filterInput = document.getElementById("filter");
  let cachedRows = [];

  function setStatus(el, ok, msg) {
    el.textContent = msg;
    el.className = "upload-status " + (ok ? "ok" : "err");
  }

  async function upload(fileInput, endpoint, statusEl) {
    const file = fileInput.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await fetch(API + endpoint, { method: "POST", body: form });
      const data = await r.json();
      if (!r.ok) {
        setStatus(statusEl, false, data.detail || "Ошибка загрузки");
        return;
      }
      setStatus(statusEl, true, "Загружено: " + data.rows + " записей (" + data.filename + ")");
      loadStats();
      loadTable();
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  // AD — кнопки по доменам
  adDomains.forEach(function (key) {
    if (adBtns[key]) {
      adBtns[key].onclick = function () { adFiles[key].click(); };
    }
    if (adFiles[key]) {
      adFiles[key].onchange = function () { upload(adFiles[key], "/api/upload/ad/" + key, adStatuses[key]); };
    }
  });

  btnMfa.onclick = function () { fileMfa.click(); };
  btnPeople.onclick = function () { filePeople.click(); };
  fileMfa.onchange = function () { upload(fileMfa, "/api/upload/mfa", statusMfa); };
  filePeople.onchange = function () { upload(filePeople, "/api/upload/people", statusPeople); };

  async function loadStats() {
    try {
      const r = await fetch(API + "/api/stats");
      const s = await r.json();
      var parts = [];
      if (s.ad_domains) {
        var adParts = [];
        for (var key in s.ad_domains) {
          var d = s.ad_domains[key];
          adParts.push(d.city + ": " + d.rows);
        }
        parts.push("AD: " + s.ad_total + " (" + adParts.join(", ") + ")");
      }
      parts.push("MFA: " + s.mfa_rows);
      parts.push("Кадры: " + s.people_rows);
      if (s.last_upload && s.last_upload.mfa) parts.push("MFA: " + s.last_upload.mfa.filename);
      if (s.last_upload && s.last_upload.people) parts.push("Кадры: " + s.last_upload.people.filename);
      statsEl.innerHTML = parts.join(" · ");
    } catch (_) {
      statsEl.textContent = "Не удалось загрузить статистику";
    }
  }

  function escapeHtml(s) {
    if (s == null || s === undefined) return "";
    const t = document.createElement("span");
    t.textContent = s;
    return t.innerHTML;
  }

  function rowClass(source) {
    if (source === "AD") return "source-ad";
    if (source === "MFA") return "source-mfa";
    if (source === "Кадры") return "source-people";
    return "";
  }

  function renderTable(rows, filterStr) {
    const filter = (filterStr || "").trim().toLowerCase();
    let visible = rows;
    if (filter) {
      visible = rows.filter(function (row) {
        return JSON.stringify(row).toLowerCase().indexOf(filter) !== -1;
      });
    }
    tbody.innerHTML = visible
        .map(function (row) {
          return (
            "<tr class=\"" +
            rowClass(row.source) +
            "\">" +
            "<td>" + escapeHtml(row.source) + "</td>" +
            "<td>" + escapeHtml(row.login) + "</td>" +
            "<td>" + escapeHtml(row.domain) + "</td>" +
            "<td>" + escapeHtml(row.uz_active) + "</td>" +
            "<td>" + escapeHtml(row.password_last_set) + "</td>" +
            "<td>" + escapeHtml(row.account_expires) + "</td>" +
            "<td>" + escapeHtml(row.staff_uuid) + "</td>" +
            "<td>" + escapeHtml(row.mfa_enabled) + "</td>" +
            "<td>" + escapeHtml(row.mfa_created_at) + "</td>" +
            "<td>" + escapeHtml(row.mfa_last_login) + "</td>" +
            "<td>" + escapeHtml(row.mfa_authenticators) + "</td>" +
            "<td>" + escapeHtml(row.fio_ad) + "</td>" +
            "<td>" + escapeHtml(row.fio_mfa) + "</td>" +
            "<td>" + escapeHtml(row.fio_people) + "</td>" +
            "<td>" + escapeHtml(row.email_ad) + "</td>" +
            "<td>" + escapeHtml(row.email_mfa) + "</td>" +
            "<td>" + escapeHtml(row.email_people) + "</td>" +
            "<td>" + escapeHtml(row.phone_ad) + "</td>" +
            "<td>" + escapeHtml(row.phone_mfa) + "</td>" +
            "<td>" + escapeHtml(row.phone_people) + "</td>" +
            "<td class=\"discrepancy\">" + escapeHtml(row.discrepancies) + "</td>" +
            "</tr>"
          );
        })
        .join("");
    var suffix = filter ? " (показано по фильтру: " + visible.length + ")" : "";
    tableFooter.textContent = "Всего записей: " + rows.length + suffix;
  }

  async function loadTable() {
    try {
      const r = await fetch(API + "/api/consolidated");
      const data = await r.json();
      cachedRows = data.rows || [];
      renderTable(cachedRows, filterInput ? filterInput.value : "");
    } catch (e) {
      tbody.innerHTML = "<tr><td colspan=\"21\">Ошибка загрузки таблицы: " + escapeHtml(e.message) + "</td></tr>";
      tableFooter.textContent = "";
    }
  }

  btnRefresh.onclick = loadTable;
  if (filterInput) {
    filterInput.addEventListener("input", function () {
      renderTable(cachedRows, filterInput.value);
    });
  }

  // Очистка БД по типу
  async function clearData(endpoint, label, statusEl) {
    if (!confirm("Очистить данные " + label + "?")) return;
    try {
      var r = await fetch(API + endpoint, { method: "DELETE" });
      var data = await r.json();
      if (r.ok) {
        setStatus(statusEl, true, "Удалено: " + data.deleted + " записей");
        loadStats();
        loadTable();
      } else {
        setStatus(statusEl, false, "Ошибка очистки");
      }
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  // Очистка AD по доменам
  var adCityNames = { izhevsk: "AD Ижевск", kostroma: "AD Кострома", moscow: "AD Москва" };
  adDomains.forEach(function (key) {
    var btn = document.getElementById("btn-clear-ad-" + key);
    if (btn) {
      btn.onclick = function () { clearData("/api/clear/ad/" + key, adCityNames[key], adStatuses[key]); };
    }
  });

  var btnClearMfa = document.getElementById("btn-clear-mfa");
  var btnClearPeople = document.getElementById("btn-clear-people");
  if (btnClearMfa) btnClearMfa.onclick = function () { clearData("/api/clear/mfa", "MFA", statusMfa); };
  if (btnClearPeople) btnClearPeople.onclick = function () { clearData("/api/clear/people", "Кадры", statusPeople); };

  // Выгрузка сводной в XLSX
  var btnExport = document.getElementById("btn-export");
  if (btnExport) {
    btnExport.onclick = function () {
      window.location.href = API + "/api/export/xlsx";
    };
  }

  // Сворачивание/разворачивание панели загрузки
  var toggleBtn = document.getElementById("toggle-uploads");
  var uploadsPanel = document.getElementById("uploads-panel");
  if (toggleBtn && uploadsPanel) {
    toggleBtn.onclick = function () {
      uploadsPanel.classList.toggle("collapsed");
      toggleBtn.textContent = uploadsPanel.classList.contains("collapsed")
        ? "Загрузка файлов \u25B6"
        : "Загрузка файлов \u25BC";
    };
  }

  loadStats();
  loadTable();
})();
