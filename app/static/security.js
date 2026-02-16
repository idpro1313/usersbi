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

    // Click → user card
    findingsEl.addEventListener("click", function (e) {
      var link = e.target.closest("[data-user-key]");
      if (!link) return;
      e.preventDefault();
      var key = link.dataset.userKey;
      if (key) window.open("/users#" + encodeURIComponent(key), "_blank");
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
