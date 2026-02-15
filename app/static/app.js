(function () {
  const API = "";
  const fileAd = document.getElementById("file-ad");
  const fileMfa = document.getElementById("file-mfa");
  const filePeople = document.getElementById("file-people");
  const btnAd = document.getElementById("btn-ad");
  const btnMfa = document.getElementById("btn-mfa");
  const btnPeople = document.getElementById("btn-people");
  const statusAd = document.getElementById("status-ad");
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
      setStatus(statusEl, true, `Загружено: ${data.rows} записей (${data.filename})`);
      loadStats();
      loadTable();
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  btnAd.onclick = () => fileAd.click();
  btnMfa.onclick = () => fileMfa.click();
  btnPeople.onclick = () => filePeople.click();
  fileAd.onchange = () => upload(fileAd, "/api/upload/ad", statusAd);
  fileMfa.onchange = () => upload(fileMfa, "/api/upload/mfa", statusMfa);
  filePeople.onchange = () => upload(filePeople, "/api/upload/people", statusPeople);

  async function loadStats() {
    try {
      const r = await fetch(API + "/api/stats");
      const s = await r.json();
      const parts = [
        `AD: ${s.ad_rows} записей`,
        `MFA: ${s.mfa_rows} записей`,
        `Кадры: ${s.people_rows} записей`,
      ];
      if (s.last_upload?.ad) parts.push(`Последняя выгрузка AD: ${s.last_upload.ad.filename}`);
      if (s.last_upload?.mfa) parts.push(`MFA: ${s.last_upload.mfa.filename}`);
      if (s.last_upload?.people) parts.push(`Кадры: ${s.last_upload.people.filename}`);
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
            "<td>" + escapeHtml(row.domain) + "</td>" +
            "<td>" + escapeHtml(row.login) + "</td>" +
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
    tableFooter.textContent =
      "Всего записей: " + rows.length + (filter ? " (показано по фильтру: " + visible.length + ")") : "";
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

  loadStats();
  loadTable();
})();
