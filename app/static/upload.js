(function () {
  var API = "";

  function setStatus(el, ok, msg) {
    el.textContent = msg;
    el.className = "upload-status " + (ok ? "ok" : "err");
  }

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

  // AD домены
  var adDomains = ["izhevsk", "kostroma", "moscow"];
  var adFiles = {}, adBtns = {}, adStatuses = {};
  adDomains.forEach(function (key) {
    adFiles[key] = document.getElementById("file-ad-" + key);
    adBtns[key] = document.getElementById("btn-ad-" + key);
    adStatuses[key] = document.getElementById("status-ad-" + key);
    if (adBtns[key]) adBtns[key].onclick = function () { adFiles[key].click(); };
    if (adFiles[key]) adFiles[key].onchange = function () { upload(adFiles[key], "/api/upload/ad/" + key, adStatuses[key]); };
  });

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

  // Статистика
  var statsEl = document.getElementById("stats");
  async function loadStats() {
    try {
      var r = await fetch(API + "/api/stats");
      var s = await r.json();
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

  // Очистка
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

  var adCityNames = { izhevsk: "AD Ижевск", kostroma: "AD Кострома", moscow: "AD Москва" };
  adDomains.forEach(function (key) {
    var btn = document.getElementById("btn-clear-ad-" + key);
    if (btn) btn.onclick = function () { clearData("/api/clear/ad/" + key, adCityNames[key], adStatuses[key]); };
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

  loadStats();
})();
