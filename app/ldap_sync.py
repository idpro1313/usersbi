# -*- coding: utf-8 -*-
"""Модуль синхронизации данных из Active Directory по LDAP."""
import logging
from datetime import datetime, timezone, timedelta

from app.config import AD_DOMAINS
from app.database import SessionLocal, get_setting
from app.auth import decrypt_value
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


def _get_ldap_config() -> dict:
    """Возвращает LDAP-конфигурацию из БД."""
    db = SessionLocal()
    try:
        user = get_setting(db, "ldap.user")
        pwd = decrypt_value(get_setting(db, "ldap.password"))
        use_ssl = get_setting(db, "ldap.use_ssl", "false").lower() in ("true", "1")
        domains = {}
        for key in AD_DOMAINS:
            domains[key] = {
                "server": get_setting(db, f"ldap.{key}.server"),
                "search_base": get_setting(db, f"ldap.{key}.search_base"),
                "enabled": get_setting(db, f"ldap.{key}.enabled", "false").lower() in ("true", "1"),
            }
        return {"user": user, "password": pwd, "use_ssl": use_ssl, "domains": domains}
    finally:
        db.close()


def is_available() -> dict:
    """Проверяет доступность LDAP-синхронизации."""
    if not _LDAP3_AVAILABLE:
        return {"available": False, "reason": "Библиотека ldap3 не установлена"}
    cfg = _get_ldap_config()
    if not cfg["user"] or not cfg["password"]:
        return {"available": False, "reason": "Не заданы учётные данные LDAP в настройках"}
    domains = {}
    for key in AD_DOMAINS:
        d = cfg["domains"].get(key, {})
        srv = d.get("server", "")
        domains[key] = {"city": AD_DOMAINS[key], "server": srv, "configured": bool(srv)}
    return {"available": True, "domains": domains}


def _filetime_to_dt(ft) -> datetime | None:
    """Конвертирует Windows FILETIME (Int64) → datetime (naive UTC) или None."""
    if not ft or ft <= 0 or ft >= _NEVER_EXPIRES:
        return None
    try:
        ts = (int(ft) - _FILETIME_UNIX_DIFF) / _FILETIME_SECOND
        return datetime(1970, 1, 1) + timedelta(seconds=ts)
    except (ValueError, OverflowError, OSError):
        return None


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

    ldap_cfg = _get_ldap_config()
    ldap_user = ldap_cfg["user"]
    ldap_password = ldap_cfg["password"]
    use_ssl = ldap_cfg["use_ssl"]

    if not ldap_user or not ldap_password:
        return [], "Не заданы учётные данные LDAP в настройках"

    dcfg = ldap_cfg["domains"].get(domain_key)
    if not dcfg:
        return [], f"Нет LDAP-конфигурации для домена: {domain_key}"

    server_addr = dcfg.get("server", "")
    if not server_addr:
        return [], f"Не задан LDAP-сервер для домена {domain_key}. Настройте в Параметрах."

    search_base = dcfg.get("search_base", "")
    city_name = AD_DOMAINS.get(domain_key, domain_key)

    try:
        port = 636 if use_ssl else 389
        server = Server(server_addr, port=port, use_ssl=use_ssl, get_info=LDAP_ALL)
        conn = Connection(server, user=ldap_user, password=ldap_password, auto_bind=True)

        logger.info("[LDAP %s] Подключено к %s:%d, search_base=%s", domain_key, server_addr, port, search_base)

        try:
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
        finally:
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
            pwd_last_set = _filetime_to_dt(pwd_raw)

            # accountExpires
            acc_raw = _attr_int(entry, "accountExpires")
            if acc_raw <= 0 or acc_raw >= _NEVER_EXPIRES:
                account_expires = "never"
                account_expiration_date = None
            else:
                account_expiration_date = _filetime_to_dt(acc_raw)
                account_expires = account_expiration_date.strftime("%d.%m.%Y") if account_expiration_date else "never"

            # memberOf → groups
            groups = _groups_str(_attr_list(entry, "memberOf"))

            rows.append({
                "domain": city_name,
                "login": norm(_attr(entry, "sAMAccountName")),
                "enabled": enabled,
                "password_last_set": pwd_last_set,
                "must_change_password": must_change,
                "account_expires": account_expires,
                "account_expiration_date": account_expiration_date,
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
