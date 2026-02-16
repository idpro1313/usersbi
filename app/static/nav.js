(function () {
  var BRAND = "Девелоника Пользователи";
  var ITEMS = [
    { href: "/upload",    label: "Загрузка" },
    { href: "/",          label: "Сводная" },
    { href: "/users",     label: "Пользователи" },
    { href: "/groups",    label: "Группы AD" },
    { href: "/structure", label: "Структура OU" },
    { href: "/org",        label: "Организация" },
    { href: "/duplicates", label: "Дубли" },
    { href: "/security",   label: "Безопасность" },
  ];

  var path = window.location.pathname.replace(/\/+$/, "") || "/";

  var links = ITEMS.map(function (item) {
    var active = (item.href === "/" ? path === "/" : path.indexOf(item.href) === 0);
    return '<a href="' + item.href + '" class="main-nav-item' + (active ? ' active' : '') + '">' + item.label + '</a>';
  }).join("");

  var html =
    '<nav class="main-nav">' +
      '<div class="main-nav-inner">' +
        '<span class="main-nav-brand">' + BRAND + '</span>' +
        '<div class="main-nav-links">' + links + '</div>' +
      '</div>' +
    '</nav>';

  var layout = document.querySelector(".layout");
  if (layout) {
    layout.insertAdjacentHTML("afterbegin", html);
  }
})();
