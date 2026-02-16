(function () {
  var API = "";
  var adDomains = ["izhevsk", "kostroma", "moscow"];
  var adCityNames = { izhevsk: "AD Ижевск", kostroma: "AD Кострома", moscow: "AD Москва" };
  var ldapMode = false;

  function setStatus(el, ok, msg) {
    if (!el) return;
    el.textContent = msg;
    el.className = "upload-status " + (ok ? "ok" : "err");
  }

  function getStatusEl(key) {
    if (ldapMode) return document.getElementById("status-ad-" + key);
    return document.getElementById("status-ad-" + key + "-f");
  }

  // ─── Загрузка файлов ───
  async function upload(fileInput, endpoint, statusEl) {
    var file = fileInput.files[0];
    if (!file) return;
    var form = new FormData();
    form.append("file", file);
    try {
      var r = await fetch(API + endpoint, { method: "POST", body: form });
      var data = await r.json();
      if (!r.ok) {
        setStatus(statusEl, false, data.detail || "Ошибка загрузки");
        return;
      }
      var msg = "Загружено: " + data.rows + " записей (" + data.filename + ")";
      if (data.skipped) msg += " | пропущено " + data.skipped + " чужих";
      setStatus(statusEl, true, msg);
      loadStats();
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  // ─── LDAP-синхронизация ───
  async function syncDomain(key) {
    var statusEl = document.getElementById("status-ad-" + key);
    setStatus(statusEl, true, "Синхронизация…");
    try {
      var r = await fetch(API + "/api/sync/ad/" + key, { method: "POST" });
      var data = await r.json();
      if (!r.ok) {
        setStatus(statusEl, false, data.detail || "Ошибка синхронизации");
        return;
      }
      setStatus(statusEl, true, "Синхронизировано: " + data.rows + " записей");
      loadStats();
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  async function syncAll() {
    adDomains.forEach(function (key) {
      var statusEl = document.getElementById("status-ad-" + key);
      setStatus(statusEl, true, "Синхронизация…");
    });
    try {
      var r = await fetch(API + "/api/sync/ad", { method: "POST" });
      var data = await r.json();
      if (data.domains) {
        adDomains.forEach(function (key) {
          var statusEl = document.getElementById("status-ad-" + key);
          var info = data.domains[key];
          if (!info) return;
          if (info.error) {
            setStatus(statusEl, false, info.error);
          } else if (info.skipped) {
            setStatus(statusEl, false, "Пропущено: " + info.reason);
          } else {
            setStatus(statusEl, true, "Синхронизировано: " + info.rows + " записей");
          }
        });
      }
      loadStats();
    } catch (e) {
      adDomains.forEach(function (key) {
        var statusEl = document.getElementById("status-ad-" + key);
        setStatus(statusEl, false, "Ошибка сети: " + e.message);
      });
    }
  }

  // ─── Определение режима: LDAP или файлы ───
  async function initMode() {
    try {
      var data = await AppUtils.fetchJSON(API + "/api/sync/status");
      if (data.available && data.domains) {
        var anyConfigured = false;
        adDomains.forEach(function (key) {
          if (data.domains[key] && data.domains[key].configured) {
            anyConfigured = true;
            var card = document.getElementById("ldap-card-" + key);
            if (card) card.style.display = "";
          }
        });
        if (anyConfigured) {
          ldapMode = true;
          document.getElementById("ldap-section").style.display = "";
          document.getElementById("file-upload-section").style.display = "none";
          return;
        }
      }
    } catch (_) { /* LDAP не доступен — файловый режим */ }
    ldapMode = false;
  }

  // ─── Привязка кнопок ───

  // Файловая загрузка AD
  adDomains.forEach(function (key) {
    var fileEl = document.getElementById("file-ad-" + key);
    var btnEl = document.getElementById("btn-ad-" + key);
    var statusEl = document.getElementById("status-ad-" + key + "-f");
    if (btnEl) btnEl.onclick = function () { if (fileEl) fileEl.click(); };
    if (fileEl) fileEl.onchange = function () { upload(fileEl, "/api/upload/ad/" + key, statusEl); };
  });

  // LDAP-синхронизация AD
  adDomains.forEach(function (key) {
    var btn = document.getElementById("btn-sync-" + key);
    if (btn) btn.onclick = function () { syncDomain(key); };
  });
  var btnSyncAll = document.getElementById("btn-sync-all");
  if (btnSyncAll) btnSyncAll.onclick = syncAll;

  // MFA + Кадры (только файлы)
  var fileMfa = document.getElementById("file-mfa");
  var filePeople = document.getElementById("file-people");
  var btnMfa = document.getElementById("btn-mfa");
  var btnPeople = document.getElementById("btn-people");
  var statusMfa = document.getElementById("status-mfa");
  var statusPeople = document.getElementById("status-people");
  btnMfa.onclick = function () { fileMfa.click(); };
  btnPeople.onclick = function () { filePeople.click(); };
  fileMfa.onchange = function () { upload(fileMfa, "/api/upload/mfa", statusMfa); };
  filePeople.onchange = function () { upload(filePeople, "/api/upload/people", statusPeople); };

  // ─── Статистика ───
  var statsEl = document.getElementById("stats");
  async function loadStats() {
    try {
      var s = await AppUtils.fetchJSON(API + "/api/stats");
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
      statsEl.innerHTML = parts.join(" &middot; ");
    } catch (_) {
      statsEl.textContent = "Не удалось загрузить статистику";
    }
  }

  // ─── Очистка ───
  async function clearData(endpoint, label, statusEl) {
    if (!confirm("Очистить данные " + label + "?")) return;
    try {
      var r = await fetch(API + endpoint, { method: "DELETE" });
      var data = await r.json();
      if (r.ok) {
        setStatus(statusEl, true, "Удалено: " + data.deleted + " записей");
        loadStats();
      } else {
        setStatus(statusEl, false, "Ошибка очистки");
      }
    } catch (e) {
      setStatus(statusEl, false, "Ошибка сети: " + e.message);
    }
  }

  // Кнопки очистки AD (обе версии: LDAP и файловая)
  adDomains.forEach(function (key) {
    var btn1 = document.getElementById("btn-clear-ad-" + key);
    var btn2 = document.getElementById("btn-clear-ad-" + key + "-f");
    var handler = function () {
      var statusEl = getStatusEl(key);
      clearData("/api/clear/ad/" + key, adCityNames[key], statusEl);
    };
    if (btn1) btn1.onclick = handler;
    if (btn2) btn2.onclick = handler;
  });

  var btnClearMfa = document.getElementById("btn-clear-mfa");
  var btnClearPeople = document.getElementById("btn-clear-people");
  if (btnClearMfa) btnClearMfa.onclick = function () { clearData("/api/clear/mfa", "MFA", statusMfa); };
  if (btnClearPeople) btnClearPeople.onclick = function () { clearData("/api/clear/people", "Кадры", statusPeople); };

  var btnClearAll = document.getElementById("btn-clear-all");
  if (btnClearAll) {
    btnClearAll.onclick = async function () {
      if (!confirm("Очистить ВСЮ базу данных (AD + MFA + Кадры)?")) return;
      try {
        var r = await fetch(API + "/api/clear/all", { method: "DELETE" });
        var data = await r.json();
        if (r.ok) {
          var d = data.deleted;
          alert("Удалено: AD " + d.ad + ", MFA " + d.mfa + ", Кадры " + d.people);
          loadStats();
        }
      } catch (e) {
        alert("Ошибка: " + e.message);
      }
    };
  }

  // ─── Инициализация ───
  initMode().then(loadStats);
})();
