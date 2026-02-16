# -*- coding: utf-8 -*-
"""Модуль синхронизации данных из Active Directory по LDAP."""
import logging
from datetime import datetime, timezone, timedelta

from app.config import (
    AD_LDAP, AD_LDAP_USER, AD_LDAP_PASSWORD, AD_LDAP_USE_SSL, AD_DOMAINS,
)
from app.utils import norm, norm_phone

logger = logging.getLogger(__name__)

try:
    from ldap3 import Server, Connection, SUBTREE, ALL as LDAP_ALL
    _LDAP3_AVAILABLE = True
except ImportError:
    _LDAP3_AVAILABLE = False

# Windows FILETIME: 100-наносекундные интервалы с 01.01.1601
_FILETIME_UNIX_DIFF = 116444736000000000
_FILETIME_SECOND = 10_000_000
_NEVER_EXPIRES = 9223372036854775807

# Атрибуты AD для запроса
_AD_ATTRS = [
    "displayName", "mail", "sAMAccountName", "title", "manager",
    "distinguishedName", "company", "department", "mobile", "l",
    "telephoneNumber", "employeeNumber", "info",
    "pwdLastSet", "accountExpires", "memberOf",
    "userAccountControl",
    "extensionAttribute1",
]


def is_available() -> dict:
    """Проверяет доступность LDAP-синхронизации."""
    if not _LDAP3_AVAILABLE:
        return {"available": False, "reason": "Библиотека ldap3 не установлена"}
    if not AD_LDAP_USER or not AD_LDAP_PASSWORD:
        return {"available": False, "reason": "Не заданы AD_LDAP_USER / AD_LDAP_PASSWORD"}
    domains = {}
    for key in AD_DOMAINS:
        cfg = AD_LDAP.get(key, {})
        srv = cfg.get("server", "")
        domains[key] = {"city": AD_DOMAINS[key], "server": srv, "configured": bool(srv)}
    return {"available": True, "domains": domains}


def _filetime_to_str(ft) -> str:
    """Конвертирует Windows FILETIME (Int64) → DD.MM.YYYY."""
    if not ft or ft <= 0 or ft >= _NEVER_EXPIRES:
        return ""
    try:
        ts = (int(ft) - _FILETIME_UNIX_DIFF) / _FILETIME_SECOND
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=ts)
        return dt.strftime("%d.%m.%Y")
    except (ValueError, OverflowError, OSError):
        return ""


def _attr(entry, name, default=""):
    """Безопасно извлекает значение атрибута из ldap3-записи."""
    try:
        val = getattr(entry, name, None)
        if val is None:
            return default
        v = val.value
        if v is None:
            return default
        return v
    except Exception:
        return default


def _attr_int(entry, name) -> int:
    """Извлекает целочисленный атрибут."""
    v = _attr(entry, name, None)
    if v is None:
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _attr_list(entry, name) -> list:
    """Извлекает многозначный атрибут как список."""
    try:
        val = getattr(entry, name, None)
        if val is None:
            return []
        v = val.value
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]
    except Exception:
        return []


def _groups_str(member_of: list) -> str:
    """memberOf (список DN) → строка с CN через '; '."""
    if not member_of:
        return ""
    names = []
    for dn in member_of:
        s = str(dn)
        if s.upper().startswith("CN="):
            names.append(s.split(",")[0][3:])
        else:
            names.append(s)
    return "; ".join(names)


def sync_domain(domain_key: str) -> tuple[list[dict], str | None]:
    """
    Запрашивает пользователей из AD по LDAP.
    Возвращает (rows, error) — формат rows идентичен parse_ad().
    """
    if not _LDAP3_AVAILABLE:
        return [], "Библиотека ldap3 не установлена"
    if not AD_LDAP_USER or not AD_LDAP_PASSWORD:
        return [], "Не заданы учётные данные LDAP (AD_LDAP_USER / AD_LDAP_PASSWORD)"

    cfg = AD_LDAP.get(domain_key)
    if not cfg:
        return [], f"Нет LDAP-конфигурации для домена: {domain_key}"

    server_addr = cfg.get("server", "")
    if not server_addr:
        return [], (
            f"Не задан LDAP-сервер для домена {domain_key}. "
            f"Установите переменную AD_LDAP_SERVER_{domain_key.upper()}"
        )

    search_base = cfg.get("search_base", "")
    city_name = AD_DOMAINS.get(domain_key, domain_key)

    try:
        port = 636 if AD_LDAP_USE_SSL else 389
        server = Server(server_addr, port=port, use_ssl=AD_LDAP_USE_SSL, get_info=LDAP_ALL)
        conn = Connection(server, user=AD_LDAP_USER, password=AD_LDAP_PASSWORD, auto_bind=True)

        logger.info("[LDAP %s] Подключено к %s:%d, search_base=%s", domain_key, server_addr, port, search_base)

        conn.search(
            search_base=search_base,
            search_filter="(&(objectClass=user)(objectCategory=person))",
            search_scope=SUBTREE,
            attributes=_AD_ATTRS,
            paged_size=1000,
        )

        entries = list(conn.entries)

        # Пагинация: дочитываем оставшиеся страницы
        cookie = conn.result.get("controls", {}).get(
            "1.2.840.113556.1.4.319", {}
        ).get("value", {}).get("cookie")
        while cookie:
            conn.search(
                search_base=search_base,
                search_filter="(&(objectClass=user)(objectCategory=person))",
                search_scope=SUBTREE,
                attributes=_AD_ATTRS,
                paged_size=1000,
                paged_cookie=cookie,
            )
            entries.extend(conn.entries)
            cookie = conn.result.get("controls", {}).get(
                "1.2.840.113556.1.4.319", {}
            ).get("value", {}).get("cookie")

        conn.unbind()
        logger.info("[LDAP %s] Получено записей: %d", domain_key, len(entries))

        rows = []
        for entry in entries:
            # userAccountControl: бит 2 (0x2) = ACCOUNTDISABLE
            uac = _attr_int(entry, "userAccountControl")
            enabled = "False" if uac & 2 else "True"

            # pwdLastSet: 0 = требуется смена пароля
            pwd_raw = _attr_int(entry, "pwdLastSet")
            must_change = "Да" if pwd_raw == 0 else "Нет"
            pwd_last_set = _filetime_to_str(pwd_raw) if pwd_raw > 0 else ""

            # accountExpires
            acc_raw = _attr_int(entry, "accountExpires")
            if acc_raw <= 0 or acc_raw >= _NEVER_EXPIRES:
                account_expires = "never"
            else:
                account_expires = _filetime_to_str(acc_raw) or "never"

            # memberOf → groups
            groups = _groups_str(_attr_list(entry, "memberOf"))

            rows.append({
                "domain": city_name,
                "login": norm(_attr(entry, "sAMAccountName")),
                "enabled": enabled,
                "password_last_set": pwd_last_set,
                "must_change_password": must_change,
                "account_expires": account_expires,
                "email": norm(_attr(entry, "mail")),
                "phone": norm_phone(_attr(entry, "telephoneNumber")),
                "mobile": norm_phone(_attr(entry, "mobile")),
                "display_name": norm(_attr(entry, "displayName")),
                "staff_uuid": norm(_attr(entry, "extensionAttribute1")),
                "title": norm(_attr(entry, "title")),
                "manager": norm(_attr(entry, "manager")),
                "distinguished_name": norm(_attr(entry, "distinguishedName")),
                "company": norm(_attr(entry, "company")),
                "department": norm(_attr(entry, "department")),
                "location": norm(_attr(entry, "l")),
                "employee_number": norm(_attr(entry, "employeeNumber")),
                "info": norm(_attr(entry, "info")),
                "groups": groups,
            })

        return rows, None

    except Exception as e:
        logger.error("[LDAP %s] Ошибка: %s", domain_key, e)
        return [], f"LDAP-ошибка ({server_addr}): {e}"
